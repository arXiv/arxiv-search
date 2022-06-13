"""Use this to initialize the search index for testing."""

import click
import time

from search.factory import create_ui_web_app
from search.services import index

app = create_ui_web_app()
app.app_context().push()


@app.cli.command()
@click.option('--wait', is_flag=True, help="Wait for the ElasticSearch service to start up")
def create_index(wait):
    """Initialize the search index."""

    if wait:
        ssec = 10
        MAX_RETRY = 10
        retry = 0
        available = False
        while retry < MAX_RETRY:
            retry = retry + 1
            try:
                print("Checking ElasticSearch availablity")
                available = index.SearchSession.cluster_available()
            except:
                print("ElasticSearch is not ready yet")
            if available:
                break
            else:
                time.sleep(ssec)

        if not available:
            raise RuntimeError(
                f"The ElasticSearch index is not available after waiting {ssec * MAX_RETRY} sec.")

    index.SearchSession.create_index()


if __name__ == "__main__":
    create_index()
