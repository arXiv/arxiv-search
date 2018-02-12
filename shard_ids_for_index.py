"""Split a list of arXiv IDs into a separate list for each web node."""

import os
import click
import sys


@click.command()
@click.option('--id_list', '-l',
              help='Print the indexable JSON to stdout.')
@click.option('--outpath', '-o', default=os.getcwd(),
              help="Directory in which to place the output lists. Defaults to"
                   " current working directory.")
@click.option('--n_shards', '-n', default=4)
def shard_ids(id_list: str, outpath: str, n_shards: int) -> None:
    """Shard the IDs in the file ``id_list`` into ``n_shards`` lists."""
    if not os.path.exists(id_list):
        click.echo(f'Path does not exist: {id_list}')
        sys.exit(1)
    if not os.path.exists(outpath):
        click.echo(f'Path does not exist: {outpath}')
        sys.exit(1)

    # Set up output files.
    click.echo(f'Shard into {n_shards} lists')
    files = {
        i: open(os.path.join(outpath, ('shard_%i.txt' % i)), 'w')
        for i in range(1, n_shards + 1)
    }

    # Shard on the final character (int) of each line.
    try:
        with open(id_list) as f:
            for line in f:
                ident = line.strip()
                affix = int(ident[-1])
                files[(affix % n_shards) + 1].write(f'{ident}\n')
    except Exception as e:
        click.echo('Ack!: %s' % str(e))
        sys.exit(1)
    finally:
        for i, f in files.items():
            f.close()


if __name__ == '__main__':
    shard_ids()
