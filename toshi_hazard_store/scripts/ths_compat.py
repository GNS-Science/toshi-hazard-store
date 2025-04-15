import pathlib

import click

from toshi_hazard_store.config import STORAGE_FOLDER
from toshi_hazard_store.model.hazard_models_manager import CompatibleHazardCalculationManager

chc_manager = CompatibleHazardCalculationManager(pathlib.Path(STORAGE_FOLDER))


#  _ __ ___   __ _(_)_ __
# | '_ ` _ \ / _` | | '_ \
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|
#
@click.group()
def main():
    """Maintain hazard compatability calculation metadata."""


@main.command()
@click.argument('unique-id', type=str)
@click.option('--notes', '-N', required=False, default=None, help="optional notes about the item")
def add(unique_id, notes):
    """Create a new hazard calculation compatability entry

    unique_id: a unique string ID.
    """
    model = dict(unique_id=unique_id, notes=notes)
    chc_manager.create(model)


@main.command()
@click.argument('unique-id', type=str)
def delete(unique_id):
    """Delete an existing hazard calculation compatability entry

    unique_id: a unique string ID.
    """
    chc_manager.delete(unique_id)


@main.command()
@click.argument('unique-id', type=str)
@click.option('--notes', '-N', required=True, help="notes about the item")
def update(unique_id, notes):
    """Update existing hazard calculation compatability notes.

    unique_id: a unique string ID.
    """
    model = dict(unique_id=unique_id, notes=notes)
    chc_manager.update(unique_id, model)


@main.command()
@click.option('--verbose', '-v', is_flag=True, default=False)
def ls(verbose):
    """List the hazard calculation compatability items."""
    for id in chc_manager.get_all_ids():
        if verbose:
            obj = chc_manager.load(id)
            click.echo(
                f"{id} {obj.created_at.isoformat(timespec='seconds')} "
                f"{obj.updated_at.isoformat(timespec='seconds')} `{obj.notes}`"
            )
        else:
            click.echo(id)
