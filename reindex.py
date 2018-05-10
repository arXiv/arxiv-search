"""Helper script to reindex all arXiv papers."""

import os
import tempfile
import click
import time

from search.factory import create_ui_web_app
from search.services import index

app = create_ui_web_app()


@app.cli.command()
@click.argument('old_index', nargs=1)
@click.argument('new_index', nargs=1)
def reindex(old_index: str, new_index: str):
    """
    Reindex the documents in `old_index` to `new_index`.

    This will create `new_index` with the current configured mappings if it
    does not already exist.
    """
    click.echo(f"Reindex papers in `{old_index}` to `{new_index}`")
    if not index.index_exists(old_index):
        click.echo(f"Source index `{old_index}` does not exist.")

    r = index.reindex(old_index, new_index)
    if not r:
        raise click.ClickException("Failed to get or create new index")

    click.echo(f"Started reindexing task")
    task_id = r['task']
    with click.progressbar(length=100, label='percent complete') as progress:
        while True:
            status = index.get_task_status(task_id)
            total = float(status['task']['status']['total'])
            if status['completed'] or total == 0:
                progress.update(100)
                break

            updated = status['task']['status']['updated']
            created = status['task']['status']['created']
            deleted = status['task']['status']['deleted']
            complete = (updated + created + deleted)/total
            progress.update(complete * 100)
            if complete == 1:
                break
            time.sleep(2)


if __name__ == '__main__':
    reindex()
