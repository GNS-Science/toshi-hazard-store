"""Prove whether disagg-rlzs Z axis is in best_rlzs order or ordinal order.

Uses poe4 (PoE stored per Z position) vs hcurves-rlzs (PoE per rlz ordinal)
as independent oracles. The OQ Extractor is queried per-realization for the hcurves.

hcurves-rlzs in this fixture has shape (n_sites, n_rlz, 1, 1) — one IMT, one level
(the iml_disagg target), giving PoE for each rlz ordinal directly without interpolation.

poe4 has shape (n_sites, n_imts, n_poes, n_Z) — PoE per Z position, where Z indexing
matches disagg-rlzs. Comparing poe4[..., z] against hcurves[ordinal, ...] for the two
competing hypotheses (best_rlzs order vs ordinal order) gives an unambiguous answer.

Requires: uv sync --group oq-compat
Run:      uv run python scripts/verify_disagg_z_ordering.py
"""

import h5py
import numpy as np

try:
    from openquake.calculators.extract import Extractor
except ImportError:
    raise SystemExit("OpenQuake not installed. Run: uv sync --group oq-compat")

HDF5 = 'tests/fixtures/oq_cross_version/disaggregation/oq_3.25.1/calc.hdf5'

extractor = Extractor(HDF5)

# Per-rlz hazard curves via OQ Extractor — keys like 'rlz-000', 'rlz-013', etc., in ordinal order.
# hcurve_dict['rlz-013'][site, imt, level] = PoE for rlz ordinal 13.
hcurve_dict = extractor.get('hcurves?kind=rlzs', asdict=True)
rlz_keys = sorted(k for k in hcurve_dict if k.startswith('rlz-'))
n_rlz = len(rlz_keys)
n_digits = max(3, len(str(n_rlz - 1)))

with h5py.File(HDF5, 'r') as f:
    best_rlzs = f['best_rlzs'][0]  # (n_rlz,) ordinals in Z-axis order
    poe4 = f['poe4'][()]  # (n_sites, n_imts, n_poes, n_Z)
    # poe4[site, imt, poe, z] = PoE achieved for the rlz at Z position z

print(f"n_rlz: {n_rlz}")
print(f"best_rlzs: {list(best_rlzs)}")
print()
print(f"{'Z':>3}  {'poe4[z]':>12}  {'hcurve[best[z]]':>16}  {'hcurve[z]':>12}  {'best match':>10}  {'ord match':>10}")
print("-" * 78)

best_wins = 0
ord_wins = 0

for z in range(n_rlz):
    poe_at_z = float(poe4[0, 0, 0, z])

    # Hypothesis A: Z position z contains data for rlz ordinal best_rlzs[z]
    best_ordinal = int(best_rlzs[z])
    poe_best_hyp = float(hcurve_dict[f'rlz-{best_ordinal:0{n_digits}d}'][0, 0, 0])

    # Hypothesis B: Z position z contains data for rlz ordinal z
    poe_ord_hyp = float(hcurve_dict[f'rlz-{z:0{n_digits}d}'][0, 0, 0])

    match_best = np.isclose(poe_at_z, poe_best_hyp, rtol=1e-5)
    match_ord = np.isclose(poe_at_z, poe_ord_hyp, rtol=1e-5)
    best_wins += match_best
    ord_wins += match_ord

    print(
        f"{z:>3}  {poe_at_z:>12.6f}  {poe_best_hyp:>16.6f}  {poe_ord_hyp:>12.6f}"
        f"  {'YES' if match_best else 'NO':>10}  {'YES' if match_ord else 'NO':>10}"
    )

print()
print(f"best_rlzs hypothesis matches: {best_wins}/{n_rlz}")
print(f"ordinal hypothesis matches:   {ord_wins}/{n_rlz}")
print()
if best_wins == n_rlz:
    print("PROVEN: Z axis is in best_rlzs order. OqHdf5Reader.disagg_rlzs() is CORRECT.")
elif ord_wins == n_rlz:
    print("WRONG: Z axis is in ordinal order. Reader needs fixing.")
else:
    print(f"Inconclusive: best={best_wins}/{n_rlz}  ord={ord_wins}/{n_rlz} — investigate.")
