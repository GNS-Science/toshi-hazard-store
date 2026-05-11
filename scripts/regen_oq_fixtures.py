#!/usr/bin/env python3
"""Generate cross-version OQ fixture HDF5 files using docker.

Runs ``oq engine --run job.ini`` inside each ``openquake/engine:<version>``
container, then writes the resulting HDF5 and a manifest JSON under
``tests/fixtures/oq_cross_version/``.

Usage
-----
# Generate all versions for both calc modes:
    uv run python scripts/regen_oq_fixtures.py --mode both

# Single version, classical only:
    uv run python scripts/regen_oq_fixtures.py --version 3.25.1 --mode classical

# Overwrite existing fixtures:
    uv run python scripts/regen_oq_fixtures.py --force

# Dry run (prints docker commands without executing):
    uv run python scripts/regen_oq_fixtures.py --dry-run

See docs/h5py_extractor_migration.md for more details.
"""

import argparse
import datetime
import glob
import hashlib
import json
import logging
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
FIXTURE_ROOT = REPO_ROOT / 'tests/fixtures/oq_cross_version'

OQ_VERSIONS = [
    '3.19.1',
    '3.20.1',
    '3.21.0',
    '3.22.1',
    '3.23.4',
    '3.24.1',
    '3.25.1',
]

_CALC_MODES = {
    'classical': REPO_ROOT / 'scratch/hazard_input',
    'disaggregation': REPO_ROOT / 'scratch/disagg_input',
}

DOCKER_IMAGE_PREFIX = 'openquake/engine'

# ── Helpers ────────────────────────────────────────────────────────────────────


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _docker_image_digest(image: str, dry_run: bool) -> str:
    """Return the image digest via ``docker inspect`` after a pull."""
    if dry_run:
        return 'sha256:<dry-run>'
    try:
        out = subprocess.check_output(
            ['docker', 'inspect', '--format', '{{index .RepoDigests 0}}', image],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip() or f'{image} (digest unavailable)'
    except subprocess.CalledProcessError:
        return f'{image} (inspect failed)'


def _pull_image(image: str, dry_run: bool) -> bool:
    """Pull a docker image. Returns True on success."""
    cmd = ['docker', 'pull', image]
    log.info('Pulling %s', image)
    if dry_run:
        print(f'[dry-run] {" ".join(cmd)}')
        return True
    result = subprocess.run(cmd)
    return result.returncode == 0


def _run_oq(version: str, mode: str, input_dir: Path, out_dir: Path, dry_run: bool) -> Path | None:
    """Run OQ inside the container and copy the resulting HDF5 to out_dir.

    Returns the path to the copied HDF5, or None on failure.
    """
    image = f'{DOCKER_IMAGE_PREFIX}:{version}'
    # The container runs oq engine, then copies the calc file to /out/.
    # OQ writes calc files to ~/oqdata/calc_<id>.hdf5 inside the container.
    run_cmd = [
        'docker', 'run', '--rm',
        '-v', f'{input_dir}:/job:ro',
        '-v', f'{out_dir}:/out',
        image,
        'bash', '-c',
        'oq engine --run /job/job.ini && cp ~/oqdata/calc_*.hdf5 /out/ 2>/dev/null || '
        'cp /root/oqdata/calc_*.hdf5 /out/ 2>/dev/null || '
        'find / -name "calc_*.hdf5" -maxdepth 6 -exec cp {} /out/ \\; 2>/dev/null; '
        'ls /out/',
    ]
    log.info('Running OQ %s %s', version, mode)
    if dry_run:
        print(f'[dry-run] {" ".join(run_cmd)}')
        return None

    result = subprocess.run(run_cmd, capture_output=False)
    if result.returncode != 0:
        log.error('OQ run failed for %s/%s (exit %d)', version, mode, result.returncode)
        return None

    # Find the produced HDF5 in out_dir.
    hdf5_files = list(out_dir.glob('calc_*.hdf5'))
    if not hdf5_files:
        log.error('No calc_*.hdf5 found in %s after OQ run for %s/%s', out_dir, version, mode)
        return None

    # Use the most-recently-modified one if there are multiple (shouldn't happen).
    hdf5_src = max(hdf5_files, key=lambda p: p.stat().st_mtime)
    dest = out_dir / 'calc.hdf5'
    hdf5_src.rename(dest)
    return dest


def _write_manifest(
    fixture_dir: Path,
    version: str,
    mode: str,
    image: str,
    digest: str,
    hdf5_path: Path,
) -> None:
    manifest = {
        'oq_version': version,
        'docker_image': image,
        'docker_image_digest': digest,
        'calc_mode': mode,
        'job_ini_source': str(_CALC_MODES[mode].relative_to(REPO_ROOT) / 'job.ini'),
        'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'hdf5_sha256': _sha256_file(hdf5_path),
        'hdf5_size_bytes': hdf5_path.stat().st_size,
        'host': platform.node(),
    }
    (fixture_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    log.info('Manifest written to %s', fixture_dir / 'manifest.json')


def _fixture_needs_regen(fixture_dir: Path) -> bool:
    """True if the fixture is absent or its HDF5 hash no longer matches the manifest."""
    manifest_path = fixture_dir / 'manifest.json'
    hdf5_path = fixture_dir / 'calc.hdf5'
    if not manifest_path.exists() or not hdf5_path.exists():
        return True
    try:
        manifest = json.loads(manifest_path.read_text())
        return _sha256_file(hdf5_path) != manifest.get('hdf5_sha256', '')
    except Exception:
        return True


# ── Main logic ─────────────────────────────────────────────────────────────────


def regen_fixture(version: str, mode: str, force: bool, dry_run: bool) -> bool:
    """Regenerate one (version, mode) fixture. Returns True on success."""
    input_dir = _CALC_MODES[mode]
    if not input_dir.exists():
        log.error('Input directory not found: %s', input_dir)
        return False

    fixture_dir = FIXTURE_ROOT / mode / f'oq_{version}'
    if not force and not _fixture_needs_regen(fixture_dir):
        log.info('Skipping %s/%s — fixture exists and hash matches', version, mode)
        return True

    image = f'{DOCKER_IMAGE_PREFIX}:{version}'

    if not _pull_image(image, dry_run):
        log.error('Failed to pull %s', image)
        return False

    image_digest = _docker_image_digest(image, dry_run)

    fixture_dir.mkdir(parents=True, exist_ok=True)
    # Use a temp dir inside fixture_dir so docker can write the HDF5 there.
    with tempfile.TemporaryDirectory(dir=fixture_dir) as tmp:
        tmp_path = Path(tmp)
        hdf5 = _run_oq(version, mode, input_dir, tmp_path, dry_run)
        if hdf5 is None:
            if dry_run:
                log.info('[dry-run] skipping manifest write')
                return True
            return False
        # Move the HDF5 out of the temp dir.
        dest = fixture_dir / 'calc.hdf5'
        shutil.move(str(hdf5), dest)

    if not dry_run:
        _write_manifest(fixture_dir, version, mode, image, image_digest, fixture_dir / 'calc.hdf5')

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', metavar='X.Y.Z', help='Regenerate a single OQ version only')
    parser.add_argument('--mode', choices=['classical', 'disaggregation', 'both'], default='both')
    parser.add_argument('--force', action='store_true', help='Overwrite existing fixtures')
    parser.add_argument('--dry-run', action='store_true', help='Print docker commands without running')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format='%(levelname)s %(message)s')

    versions = [args.version] if args.version else OQ_VERSIONS
    modes = list(_CALC_MODES.keys()) if args.mode == 'both' else [args.mode]

    failures = []
    for ver in versions:
        for mode in modes:
            ok = regen_fixture(ver, mode, args.force, args.dry_run)
            if not ok:
                failures.append((ver, mode))

    if failures:
        log.error('Failed fixtures: %s', failures)
        return 1
    log.info('All fixtures complete.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
