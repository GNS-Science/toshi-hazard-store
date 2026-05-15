#!/usr/bin/env python3
"""Capture canonical OQ Extractor output for a given calc.hdf5.

Run this script INSIDE an openquake/engine container — it imports
``openquake`` directly.  It writes two files into <output_dir>:

    extractor_snapshot.npz   -- numpy arrays (compressed)
    extractor_snapshot.json  -- all non-array metadata

Usage
-----
    python extract_snapshot.py <calc_hdf5> <mode> <output_dir>

Arguments
---------
calc_hdf5   Path to the calc.hdf5 produced by ``oq engine``.
mode        ``classical`` or ``disaggregation``.
output_dir  Directory to write the two snapshot files into (must exist).

Invoked by scripts/regen_oq_fixtures.py inside a second container after
oq engine has finished.
"""

import json
import sys
from pathlib import Path

import numpy as np


def _decode(v):
    return v.decode() if isinstance(v, bytes) else v


def _extract_classical(extractor):
    arrays = {}
    meta = {}

    df = extractor.get('sitecol').to_dframe()
    for col in ('lat', 'lon', 'vs30'):
        arrays[f'sitecol__{col}'] = df[col].values

    hcurves = extractor.get('hcurves?kind=rlzs', asdict=True)
    rlz_keys = sorted(k for k in hcurves if 'rlz-' in k)
    for key in rlz_keys:
        # npz keys must be valid Python identifiers — replace hyphen with underscore
        arrays['hcurves_rlzs__' + key.replace('-', '_')] = hcurves[key]
    meta['hcurves_rlzs_keys'] = rlz_keys

    rlzs = list(extractor.get('full_lt').get_realizations())
    meta['realizations'] = [
        {
            'ordinal': int(r.ordinal),
            'sm_lt_path': list(r.sm_lt_path),
            'gsim_lt_path': list(r.gsim_lt_path),
        }
        for r in rlzs
    ]

    return arrays, meta


def _extract_disagg(extractor, oqparam):
    arrays = {}
    meta = {}

    df = extractor.get('sitecol').to_dframe()
    for col in ('lat', 'lon', 'vs30'):
        arrays[f'sitecol__{col}'] = df[col].values

    rlzs = list(extractor.get('full_lt').get_realizations())
    meta['realizations'] = [
        {
            'ordinal': int(r.ordinal),
            'sm_lt_path': list(r.sm_lt_path),
            'gsim_lt_path': list(r.gsim_lt_path),
        }
        for r in rlzs
    ]

    kinds = oqparam.get('disagg_outputs', [])
    kind = next((k for k in kinds if 'Mag' in k and 'Dist' in k), kinds[0])
    imt = next(iter(oqparam['iml_disagg']))

    probe = extractor.get(f'disagg?kind={kind}&imt={imt}&site_id=0&poe_id=0&spec=rlzs')
    arrays['disagg__array'] = probe.array

    disagg_bins = {}
    for ax in kind.split('_'):
        ax_lo = ax.lower()
        raw = list(getattr(probe, ax_lo))
        decoded = [_decode(v) for v in raw]
        if decoded and isinstance(decoded[0], str):
            disagg_bins[ax_lo] = decoded
        else:
            disagg_bins[ax_lo] = [float(v) for v in decoded]

    meta['kind'] = kind
    meta['imt'] = imt
    meta['shape_descr'] = [_decode(d) for d in probe.shape_descr]
    meta['rlz_labels'] = [_decode(v) for v in probe.extra]
    meta['disagg_bins'] = disagg_bins

    return arrays, meta


def main():
    if len(sys.argv) != 4:
        print(f'Usage: {sys.argv[0]} <calc_hdf5> <mode> <output_dir>', file=sys.stderr)
        sys.exit(1)

    calc_hdf5 = Path(sys.argv[1])
    mode = sys.argv[2]
    output_dir = Path(sys.argv[3])

    if mode not in ('classical', 'disaggregation'):
        print(f'mode must be classical or disaggregation, got: {mode!r}', file=sys.stderr)
        sys.exit(1)

    from openquake.calculators.extract import Extractor

    # OQ's Extractor parses the calc_id integer from the filename via the regex
    # calc_(\d+)\.hdf5.  Our fixtures are committed as "calc.hdf5" which fails
    # that parse.  Symlink to a name OQ accepts; h5py follows symlinks transparently.
    calc_link = Path('/tmp/calc_1.hdf5')
    if calc_link.exists() or calc_link.is_symlink():
        calc_link.unlink()
    calc_link.symlink_to(calc_hdf5.resolve())

    extractor = Extractor(str(calc_link))
    oqparam = json.loads(extractor.get('oqparam').json)

    if mode == 'classical':
        arrays, meta = _extract_classical(extractor)
    else:
        arrays, meta = _extract_disagg(extractor, oqparam)

    meta['mode'] = mode
    meta['oqparam_json'] = extractor.get('oqparam').json
    meta['npz_keys'] = list(arrays.keys())

    npz_path = output_dir / 'extractor_snapshot.npz'
    json_path = output_dir / 'extractor_snapshot.json'

    np.savez_compressed(str(npz_path), **arrays)
    json_path.write_text(json.dumps(meta, sort_keys=True, indent=2))

    print(f'Snapshot written: {npz_path} ({npz_path.stat().st_size:,} bytes)', flush=True)
    print(f'Sidecar written:  {json_path} ({json_path.stat().st_size:,} bytes)', flush=True)


if __name__ == '__main__':
    main()
