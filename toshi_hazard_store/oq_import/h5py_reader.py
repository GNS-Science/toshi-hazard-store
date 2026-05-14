"""Direct h5py reader for OpenQuake HDF5 output files.

Replaces ``openquake.calculators.extract.Extractor`` with stable reads against the HDF5
layout, which is consistent across OQ versions while the Extractor Python API is not.

See ``docs/h5py_extractor_migration.md`` for the layout reference and cross-version notes.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Fields that may be present in sitecol/ — order doesn't matter.
_SITECOL_FIELDS = ('sids', 'lon', 'lat', 'depth', 'vs30', 'vs30measured', 'z1pt0', 'z2pt5', 'backarc')


@dataclass
class RlzRecord:
    """A single realization record as produced by OqHdf5Reader.realizations()."""

    source_path: tuple
    gsim_path: tuple
    ordinal: int


class DisaggExtract:
    """Proxy for a disagg query result — mirrors the surface used by generate_disagg_record_batches.

    **Ordering note**: the Z axis of ``disagg-rlzs/<kind>`` is NOT in rlz ordinal order.
    OQ stores disagg results in ``best_rlzs[site_idx]`` order — the realizations closest to
    the mean hazard curve, in the order OQ selected them (empirically verified via ``poe4``).
    ``rlz_labels[z]`` gives the string label (``'rlzN'``) for the rlz whose data is at Z
    position z; ``rlz_ordinals[z]`` gives the integer ordinal N directly.

    This is the opposite of ``hcurves_rlzs()``, whose keys ARE in ordinal order.
    """

    def __init__(
        self,
        array: np.ndarray,
        shape_descr: list[str],
        rlz_labels: list[str],
        bins: dict[str, Any],
    ) -> None:
        self.array = array  # shape: (*kind_bins, imt=1, poe=1, n_rlz)
        self.shape_descr = shape_descr  # e.g. ['mag', 'dist', 'imt', 'poe']
        self.rlz_labels = rlz_labels  # 'rlzN' per Z position in best_rlzs order
        self._bins = bins  # {axis_name: bin_centres_array_or_list}

    @property
    def rlz_ordinals(self) -> list[int]:
        """Integer ordinal for each Z position: ``int(rlz_labels[z][3:])`` for each z."""
        return [int(lbl[3:]) for lbl in self.rlz_labels]

    def __getattr__(self, name: str) -> Any:
        # Allows getattr(probe, 'mag'), getattr(probe, 'trt'), etc.
        try:
            return object.__getattribute__(self, '_bins')[name]
        except KeyError:
            raise AttributeError(f'{type(self).__name__!r} has no attribute {name!r}')


class OqHdf5Reader:
    """Read OpenQuake calculation HDF5 files directly with h5py.

    Exposes exactly the data surface needed by the THS extraction pipeline,
    independent of the installed openquake-engine version.
    """

    def __init__(self, hdf5_path: str | Path) -> None:
        self.path = Path(hdf5_path)

    # ------------------------------------------------------------------
    # Core data accessors
    # ------------------------------------------------------------------

    def oqparam(self) -> dict:
        """Return the OQ job configuration as a plain dict (decoded from JSON blob)."""
        with h5py.File(self.path, 'r') as f:
            raw = f['oqparam'][()]
            cfg = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return cfg

    def sitecol(self) -> pd.DataFrame:
        """Return a DataFrame of site parameters from parallel ``sitecol/*`` arrays."""
        with h5py.File(self.path, 'r') as f:
            cols = {k: f[f'sitecol/{k}'][()] for k in _SITECOL_FIELDS if f'sitecol/{k}' in f}
        return pd.DataFrame(cols)

    def hcurves_rlzs(self) -> dict[str, np.ndarray]:
        """Return per-realization hazard curves as ``{rlz-N: array(n_sites, n_imts, n_levels)}``.

        ``hcurves-rlzs`` shape is ``(n_sites, n_rlz, n_imts, n_levels)``; this method slices
        along the rlz axis and returns one 3-D array per realization.

        Keys are zero-padded rlz ordinal strings (``'rlz-000'``, ``'rlz-001'``, …) **in ordinal
        order**: ``'rlz-NNN'`` corresponds to column N (axis 1) of ``hcurves-rlzs``, matching
        ``realizations()[N].ordinal``.  This is the opposite of ``disagg_rlzs()``, whose Z axis
        follows ``best_rlzs`` order rather than ordinal order.
        """
        with h5py.File(self.path, 'r') as f:
            arr = f['hcurves-rlzs'][()]  # (n_sites, n_rlz, n_imts, n_levels)
        n_rlz = arr.shape[1]
        # Match OQ Extractor key format: zero-pad to at least 3 digits.
        n_digits = max(3, len(str(n_rlz - 1)))
        return {f'rlz-{i:0{n_digits}d}': arr[:, i, :, :] for i in range(n_rlz)}

    # ------------------------------------------------------------------
    # Logic-tree / realization accessors
    # ------------------------------------------------------------------

    def gsim_branches(self) -> dict[str, str]:
        """Return ``{branch_id: uncertainty_string}`` from ``full_lt/gsim_lt``.

        The uncertainty string is the raw GSIM ``[ClassName]\\nparam=val`` bytes
        decoded to str.  nzshm_model parses either the raw or OQ-normalised form
        and produces identical hash digests — no whitespace normalisation is needed.
        """
        with h5py.File(self.path, 'r') as f:
            glt = f['full_lt']['gsim_lt']
            return {row['branch'].decode(): row['uncertainty'].decode() for row in glt}

    def source_branches(self) -> dict[str, str]:
        """Return a mapping whose **values** are the sm_lt_path strings used in realizations.

        The keys are internal zero-based indices and carry no semantic meaning.
        Callers that build a ``source_map`` keyed by these values (e.g.
        ``build_rlz_source_map``) rely on the values matching ``rlz.source_path[0]``.
        """
        with h5py.File(self.path, 'r') as f:
            slt = f['full_lt']['source_model_lt']
            # ``branch`` column = sm_lt_path string, e.g. '[dmgeologic, tdTrue, ...]'
            return {str(i): row['branch'].decode() for i, row in enumerate(slt)}

    def realizations(self) -> list[RlzRecord]:
        """Reconstruct the realization list from ``full_lt/sm_data`` + ``full_lt/gsim_lt``.

        Ordering matches OQ enumeration for ``number_of_logic_tree_samples = 0``:
        for each source model in declaration order, iterate the next ``samples`` gsim
        branches (also in declaration order). Note that these may not be the order in which
        realizations are stored in the hdf5.
        """
        with h5py.File(self.path, 'r') as f:
            glt = f['full_lt']['gsim_lt']
            gsim_ids = [row['branch'].decode() for row in glt]
            sm_data = f['full_lt']['sm_data']
            rlzs: list[RlzRecord] = []
            ordinal = 0
            gsim_offset = 0
            for sm_row in sm_data:
                sm_path = sm_row['path'].decode()
                n_samples = int(sm_row['samples'])
                for j in range(n_samples):
                    rlzs.append(
                        RlzRecord(
                            source_path=(sm_path,),
                            gsim_path=(gsim_ids[gsim_offset + j],),
                            ordinal=ordinal,
                        )
                    )
                    ordinal += 1
                gsim_offset += n_samples
        return rlzs

    # ------------------------------------------------------------------
    # Disaggregation accessor
    # ------------------------------------------------------------------

    def disagg_rlzs(
        self,
        kind: str,
        site_idx: int = 0,
        imt_idx: int = 0,
        poe_idx: int = 0,
    ) -> DisaggExtract:
        """Read ``disagg-rlzs/<kind>`` and return a :class:`DisaggExtract`.

        - ``.array`` — shape ``(*kind_bins, imt=1, poe=1, n_rlz)``
        - ``.shape_descr`` — axis names including ``'imt'`` and ``'poe'``
        - ``.rlz_labels`` — ``'rlzN'`` per Z position; N is the rlz ordinal at that position
        - ``.rlz_ordinals`` — integer ordinal per Z position (same info as rlz_labels)
        - ``getattr(probe, axis_name)`` — bin centres (numeric axes) or labels (TRT)
        """
        with h5py.File(self.path, 'r') as f:
            ds = f[f'disagg-rlzs/{kind}']
            arr = ds[()]  # shape: (n_sites, *kind_axes, n_imt, n_poe, n_rlz)  [OQ >= 3.24]
            # or:    (n_sites, *kind_axes, n_imt, n_poe)          [OQ <  3.24, rlz merged into poe]

            kind_axes = kind.split('_')  # e.g. ['Mag', 'Dist']
            k = len(kind_axes)

            # Slice on site, preserve imt/poe as size-1 dims so the consumer can squeeze them.
            imt_sl = slice(imt_idx, imt_idx + 1)
            poe_sl = slice(poe_idx, poe_idx + 1)
            idx = (site_idx,) + (slice(None),) * k + (imt_sl, poe_sl, slice(None))
            sliced = arr[idx]  # shape: (*kind_bins, 1, 1, n_rlz)

            # rlz labels from best_rlzs ordering (NOT ordinal order — see class docstring)
            best = f['best_rlzs'][site_idx]
            rlz_labels = [f'rlz{int(i)}' for i in best]

            # Bin centres per kind axis
            bins: dict[str, Any] = {}
            for ax in kind_axes:
                raw = f[f'disagg-bins/{ax}'][()]
                if raw.dtype.kind in ('S', 'O', 'U'):  # bytes / string dtypes
                    bins[ax.lower()] = [v.decode() if isinstance(v, bytes) else str(v) for v in raw]
                else:
                    # Numeric: stored as bin edges; compute midpoints.
                    bins[ax.lower()] = (raw[:-1] + raw[1:]) / 2.0

            shape_descr = [ax.lower() for ax in kind_axes] + ['imt', 'poe']

        return DisaggExtract(array=sliced, shape_descr=shape_descr, rlz_labels=rlz_labels, bins=bins)
