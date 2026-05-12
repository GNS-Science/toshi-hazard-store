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
import hashlib
import json
import logging
import os
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

_INPUT_DIR = REPO_ROOT / 'scripts/oq_input'

_CALC_MODES = {
    'classical': _INPUT_DIR,
    'disaggregation': _INPUT_DIR,
}

_CALC_JOB_INIS = {
    'classical': 'job_classical.ini',
    'disaggregation': 'job_disagg.ini',
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


def _run_oq(version: str, mode: str, input_dir: Path, job_ini: str, out_dir: Path, dry_run: bool) -> Path | None:
    """Run OQ inside the container and copy the resulting HDF5 to out_dir.

    Uses ``docker cp`` (host-side) rather than a bind-mount so container-user
    write permissions on the output directory are never an issue.

    Returns the path to the copied HDF5 (inside out_dir), or None on failure.
    """
    import uuid

    image = f'{DOCKER_IMAGE_PREFIX}:{version}'
    container_name = f'oq-regen-{uuid.uuid4().hex[:8]}'

    # Adapt CMD to the image's configured entrypoint.
    # OQ 3.19–3.24: entrypoint = ["/bin/bash", "-c"] — CMD must be a single string
    #   so the effective call is /bin/bash -c "oq engine --run /job/job.ini".
    #   Passing ["bash", "-c", "oq engine ..."] would make bash treat "bash" as the
    #   command string, silently starting and immediately exiting without running OQ.
    # OQ 3.25+:     entrypoint = ["./oq-start.sh"] — pass CMD as separate tokens.
    try:
        ep_raw = subprocess.check_output(
            ['docker', 'inspect', '--format', '{{json .Config.Entrypoint}}', image],
            stderr=subprocess.DEVNULL,
        )
        entrypoint = json.loads(ep_raw.decode().strip())
    except Exception:
        entrypoint = []

    if entrypoint == ['/bin/bash', '-c']:
        oq_cmd = [f'oq engine --run /job/{job_ini}']  # single string for bash -c entrypoint
    else:
        oq_cmd = ['bash', '-c', f'oq engine --run /job/{job_ini}']

    run_cmd = [
        'docker', 'run',
        '--name', container_name,
        '-v', f'{input_dir}:/job:ro',
        image,
    ] + oq_cmd
    log.info('Running OQ %s %s (entrypoint: %s)', version, mode, entrypoint)
    if dry_run:
        print(f'[dry-run] {" ".join(run_cmd)}')
        return None

    result = subprocess.run(run_cmd)

    hdf5_path = None
    if result.returncode == 0:
        # OQ writes to ~/oqdata/calc_<id>.hdf5 in the container.  Try the two
        # known home paths; use docker cp (host user) so no container-side
        # write permission is needed.  The trailing "/." copies contents of the
        # directory, not the directory itself, directly into out_dir.
        for oqdata in ['/home/openquake/oqdata', '/root/oqdata']:
            cp = subprocess.run(
                ['docker', 'cp', f'{container_name}:{oqdata}/.', str(out_dir)],
                capture_output=True,
            )
            if cp.returncode == 0:
                found = list(out_dir.glob('calc_*.hdf5'))
                if found:
                    hdf5_path = max(found, key=lambda p: p.stat().st_mtime)
                    break

    # Always remove the (now stopped) container.
    subprocess.run(['docker', 'rm', container_name], capture_output=True)

    if result.returncode != 0:
        log.error('OQ run failed for %s/%s (exit %d)', version, mode, result.returncode)
        return None
    if hdf5_path is None:
        log.error('No calc_*.hdf5 found for %s/%s', version, mode)
        return None

    dest = out_dir / 'calc.hdf5'
    hdf5_path.rename(dest)
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
        'job_ini_source': str(_CALC_MODES[mode].relative_to(REPO_ROOT) / _CALC_JOB_INIS[mode]),
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
    job_ini = _CALC_JOB_INIS[mode]
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
        os.chmod(tmp_path, 0o777)  # container runs as non-root; mount point must be world-writable
        hdf5 = _run_oq(version, mode, input_dir, job_ini, tmp_path, dry_run)
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
