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
    """Self-describing disagg result for a single realization.

    ``disagg_rlzs()`` returns a ``dict[str, DisaggExtract]`` keyed by ``'rlz-NNN'`` (the
    same format as ``hcurves_rlzs()``).  Each entry covers one rlz; the rlz ordinal is
    encoded in the dict key, so ``rlz_labels`` / ``rlz_ordinals`` are not needed here.

    **Axis ordering note**: the dict key order follows ``best_rlzs[site_idx]`` (per-site
    permutation), not rlz ordinal order — the same ordering used by OQ internally.
    """

    def __init__(
        self,
        array: np.ndarray,
        shape_descr: list[str],
        bins: dict[str, Any],
    ) -> None:
        self.array = array  # shape: (*kind_bins, imt=1, poe=1) — one rlz
        self.shape_descr = shape_descr  # e.g. ['mag', 'dist', 'imt', 'poe']
        self._bins = bins  # {axis_name: bin_centres_array_or_list}

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
    ) -> dict[str, DisaggExtract]:
        """Read ``disagg-rlzs/<kind>`` and return ``{'rlz-NNN': DisaggExtract, ...}``.

        Mirrors ``hcurves_rlzs()``: dict keyed by zero-padded ``'rlz-NNN'`` strings,
        one entry per realization.  Each :class:`DisaggExtract` value holds:

        - ``.array`` — shape ``(*kind_bins, imt=1, poe=1)`` for this single rlz
        - ``.shape_descr`` — axis names including ``'imt'`` and ``'poe'``
        - ``getattr(entry, axis_name)`` — bin centres (numeric) or labels (TRT)

        Bin metadata (``shape_descr``, per-axis bins) is shared by reference across all
        entries — accessing it on any entry is equivalent.

        **Key order**: ``best_rlzs[site_idx]`` order (per-site permutation set by OQ),
        not rlz ordinal order.  The rlz ordinal is encoded in the key: ``'rlz-005'``
        means ordinal 5.  This is the same Z-axis ordering used by OQ internally.
        """
        with h5py.File(self.path, 'r') as f:
            arr = f[f'disagg-rlzs/{kind}'][()]  # (n_sites, *kind_axes, n_imt, n_poe, n_rlz)

            kind_axes = kind.split('_')  # e.g. ['Mag', 'Dist']
            k = len(kind_axes)

            # Slice on site, preserve imt/poe as size-1 dims so callers can squeeze them.
            imt_sl = slice(imt_idx, imt_idx + 1)
            poe_sl = slice(poe_idx, poe_idx + 1)
            idx = (site_idx,) + (slice(None),) * k + (imt_sl, poe_sl, slice(None))
            sliced = arr[idx]  # shape: (*kind_bins, 1, 1, n_rlz)

            best = f['best_rlzs'][site_idx]  # ordinals in Z-axis order

            # Bin centres per kind axis — shared across all per-rlz entries.
            bins: dict[str, Any] = {}
            for ax in kind_axes:
                raw = f[f'disagg-bins/{ax}'][()]
                if raw.dtype.kind in ('S', 'O', 'U'):  # bytes / string dtypes
                    bins[ax.lower()] = [v.decode() if isinstance(v, bytes) else str(v) for v in raw]
                else:
                    # Numeric: stored as bin edges; compute midpoints.
                    bins[ax.lower()] = (raw[:-1] + raw[1:]) / 2.0

            shape_descr = [ax.lower() for ax in kind_axes] + ['imt', 'poe']

        n_rlz = sliced.shape[-1]
        n_digits = max(3, len(str(n_rlz - 1)))
        return {
            f'rlz-{int(best[z]):0{n_digits}d}': DisaggExtract(
                array=sliced[..., z],  # (*kind_bins, 1, 1)
                shape_descr=shape_descr,
                bins=bins,
            )
            for z in range(n_rlz)
        }
