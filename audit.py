"""Check for missing papers in the index."""

import time
import os
import csv
from multiprocessing import Pool
from functools import reduce
from operator import concat
from typing import List, Tuple

import click

from search.factory import create_ui_web_app

app = create_ui_web_app()


def exists(chunk: List[str]) -> List[Tuple[str, bool]]:
    """
    Check the status of a chunk of paper IDs.

    Parameters
    ----------
    chunk : list
        Each item should be a paper ID with a version affix.

    Returns
    -------
    list
        Items are paper ID, bool (exists) tuples.

    """
    with app.app_context():
        from search.services import index

        status = []
        for ident in chunk:
            time.sleep(0.05)  # TODO: make this configurable?
            status.append((ident, index.SearchSession.exists(ident)))
        return status


@app.cli.command()
@click.option(
    "--id_list", "-l", help="Index paper IDs in a file (one ID per line)"
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=1_600,
    help="Number of records to process each iteration",
)
@click.option("--n-workers", "-n", type=int, default=8, help="Num of workers")
@click.option("--output", "-o", help="File in which missing IDs are stored")
def audit(id_list: str, batch_size: int, n_workers: int, output: str):
    """
    Check the index for missing papers.

    Uses HEAD requests to the document endpoint using each paper ID in the
    provided list. Uses multiprocessing with a configurable number of worker
    processes to speed things up.

    Parameters
    ----------
    id_list : str
        Should be a path to a file with paper IDs. There should be one paper ID
        per line. Paper IDs should include version affixes.
    batch_size : int
        Number of records per batch. Each batch is divided into equal chunks
        and distributed across workers. Smaller batches mean more frequent
        updates/checkpoints. Must be divisible by the number of workers.
        Default: 1,600.
    n_workers : int
        Number of worker processes to run for each batch. Default: 8.
    output : str
        Path to a file into which to deposit paper IDs not found in the index.

    """
    if batch_size % n_workers > 0:
        raise click.ClickException(
            "batch size must be divisible by the number of workers"
        )
    chunk_size = int(round(batch_size / n_workers))

    if not os.path.exists(id_list):
        raise click.ClickException("no such file")

    # Load paper IDs to check.
    with open(id_list) as f:
        data = [row[0] for row in csv.reader(f)]

    # Create the output file.
    with open(output, "w") as f:
        f.write("")

    N_results = 0
    N_total = len(data)

    with click.progressbar(length=N_total, label="Papers checked") as bar:
        # We do this in batches, so that we can track and save as we go.
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            chunks = [
                batch[c : c + chunk_size]
                for c in range(0, batch_size, chunk_size)
            ]

            with Pool(n_workers) as p:
                results = reduce(concat, p.map(exists, chunks))

            # Write one missing paper ID per line.
            with open(output, "a") as f:  # Append to output file.
                for ident, status in results:
                    if status:
                        continue
                    f.write(f"{ident}\n")

            N_results += len(results)
            bar.update(N_results)


if __name__ == "__main__":
    audit()
