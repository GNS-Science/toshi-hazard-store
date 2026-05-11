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
class _RlzRecord:
    """A single realization record as produced by OqHdf5Reader.realizations()."""

    source_path: tuple
    gsim_path: tuple
    ordinal: int


class _DisaggExtract:
    """Proxy for a disagg query result — mirrors the surface used by generate_disagg_record_batches."""

    def __init__(
        self,
        array: np.ndarray,
        shape_descr: list[str],
        extra: list[str],
        bins: dict[str, Any],
    ) -> None:
        self.array = array          # shape: (*kind_bins, imt=1, poe=1, n_rlz)
        self.shape_descr = shape_descr  # e.g. ['mag', 'dist', 'imt', 'poe']
        self.extra = extra          # rlz labels e.g. ['rlz4', 'rlz11', ...]
        self._bins = bins           # {axis_name: bin_centres_array_or_list}

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

    def realizations(self) -> list[_RlzRecord]:
        """Reconstruct the realization list from ``full_lt/sm_data`` + ``full_lt/gsim_lt``.

        Ordering matches OQ enumeration for ``number_of_logic_tree_samples = 0``:
        for each source model in declaration order, iterate the next ``samples`` gsim
        branches (also in declaration order).
        """
        with h5py.File(self.path, 'r') as f:
            glt = f['full_lt']['gsim_lt']
            gsim_ids = [row['branch'].decode() for row in glt]
            sm_data = f['full_lt']['sm_data']
            rlzs: list[_RlzRecord] = []
            ordinal = 0
            gsim_offset = 0
            for sm_row in sm_data:
                sm_path = sm_row['path'].decode()
                n_samples = int(sm_row['samples'])
                for j in range(n_samples):
                    rlzs.append(
                        _RlzRecord(
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
    ) -> _DisaggExtract:
        """Read ``disagg-rlzs/<kind>`` and return a probe-like object.

        The returned ``_DisaggExtract`` mirrors the Extractor probe surface used by
        ``generate_disagg_record_batches``:
        - ``.array`` — shape ``(*kind_bins, imt=1, poe=1, n_rlz)``
        - ``.shape_descr`` — axis names including ``'imt'`` and ``'poe'``
        - ``.extra`` — rlz label strings ``['rlzN', ...]`` in ``best_rlzs`` order
        - ``getattr(probe, axis_name)`` — bin centres (numeric axes) or labels (TRT)

        Cross-version note: OQ < 3.24 stored disagg arrays without the separate trailing
        rlz dimension; that variant is normalised here so callers see a consistent shape.
        """
        with h5py.File(self.path, 'r') as f:
            ds = f[f'disagg-rlzs/{kind}']
            arr = ds[()]  # shape: (n_sites, *kind_axes, n_imt, n_poe, n_rlz)  [OQ >= 3.24]
                          # or:    (n_sites, *kind_axes, n_imt, n_poe)          [OQ <  3.24, rlz merged into poe]

            kind_axes = kind.split('_')  # e.g. ['Mag', 'Dist']
            k = len(kind_axes)

            arr = self._normalise_disagg_shape(arr, k)
            # arr is now guaranteed: (n_sites, *kind_bins, n_imt, n_poe, n_rlz)

            # Slice on site, preserve imt/poe as size-1 dims so the consumer can squeeze them.
            imt_sl = slice(imt_idx, imt_idx + 1)
            poe_sl = slice(poe_idx, poe_idx + 1)
            idx = (site_idx,) + (slice(None),) * k + (imt_sl, poe_sl, slice(None))
            sliced = arr[idx]  # shape: (*kind_bins, 1, 1, n_rlz)

            # rlz labels from best_rlzs ordering
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

        return _DisaggExtract(array=sliced, shape_descr=shape_descr, extra=rlz_labels, bins=bins)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_disagg_shape(arr: np.ndarray, n_kind_axes: int) -> np.ndarray:
        """Ensure disagg array always has a separate trailing rlz axis.

        OQ < 3.24 stored spec=rlzs results without a distinct trailing rlz dimension;
        instead, the rlz count was merged into the poe axis.  This can be detected
        by comparing the actual ndim to the expected ndim for the post-3.24 layout:
        ``1 (site) + n_kind_axes + 1 (imt) + 1 (poe) + 1 (rlz) = n_kind_axes + 4``.

        If the array has one fewer dimension, it matches the old layout; we insert a
        unit rlz axis at the end so downstream code sees a consistent shape.
        Note: when the old layout folds rlzs into the poe slot, the array contains
        the raw conditional disaggregation matrices (not normalised per rlz); the
        caller must be aware that the values may differ from the post-3.24 convention.
        """
        expected_ndim = n_kind_axes + 4  # site + kind_axes + imt + poe + rlz
        if arr.ndim == expected_ndim:
            return arr  # modern layout: already correct
        if arr.ndim == expected_ndim - 1:
            log.warning(
                'disagg-rlzs array has %d dims (expected %d): '
                'looks like OQ <3.24 layout where rlz count is in the poe axis. '
                'Inserting a trailing unit axis — values may differ from OQ >=3.24.',
                arr.ndim,
                expected_ndim,
            )
            return arr[..., np.newaxis]
        raise ValueError(
            f'disagg-rlzs array has unexpected ndim={arr.ndim} '
            f'(expected {expected_ndim} or {expected_ndim - 1} for n_kind_axes={n_kind_axes})'
        )
