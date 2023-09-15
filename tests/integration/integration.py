"""Functions to startup and tear down integration env."""

import os
import time
import tempfile
import subprocess

import boto3
import click


@click.command()
def setup_for_integration_test():
    """Setups elasticsearch and kenisis for an integration test"""
    state = {}

    os.environ["ELASTICSEARCH_SERVICE_HOST"] = "localhost"
    os.environ["ELASTICSEARCH_SERVICE_PORT"] = "9201"
    os.environ["ELASTICSEARCH_SERVICE_PORT_9201_PROTO"] = "http"
    os.environ["ELASTICSEARCH_VERIFY"] = "false"

    os.environ["KINESIS_STREAM"] = "MetadataIsAvailable"
    os.environ["KINESIS_SHARD_ID"] = "0"
    os.environ["KINESIS_CHECKPOINT_VOLUME"] = tempfile.mkdtemp()
    os.environ["KINESIS_ENDPOINT"] = "http://127.0.0.1:6568"
    os.environ["KINESIS_VERIFY"] = "false"
    os.environ["KINESIS_START_TYPE"] = "TRIM_HORIZON"

    print("pulling localstack image")
    subprocess.run(
        "docker pull atlassianlabs/localstack",
        shell=True, check=True
    )

    print("starting localstack")
    start_localstack = subprocess.run(
        "docker run -d -p 6568:4568 --name integration-test-localstack atlassianlabs/localstack",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    )
    if start_localstack.returncode != 0:
        raise RuntimeError(
            f"Could not start localstack: {start_localstack.stdout}."
            f" Is the container already running? Is the container stoped but exists? Is port 6568 available?"
        )
    state["ls_container"] = start_localstack.stdout.decode("ascii").strip()
    print(f"localstack started as {state['ls_container']}")
    
    print("Building elasticsearch")
    es_build = subprocess.run(
        "docker build --file Dockerfile-elasticsearch --label arxiv/elasticsearch .",
        shell=True,check=True)

    es_run = subprocess.run(
        "docker run -d -p 9200:9200 -p 9300:9300 "
        "--name integration-test-elasticsearch arxiv/elasticsearch "
        "--env http.host=0.0.0.0 --env transport.host=127.0.0.1",
        stdout=subprocess.PIPE,
        shell=True)
    if es_run.returncode != 0:
        raise RuntimeError(f"Could not run elasticsearch: {es_run.stdout}")

    state["es_container"] = es_run.stdout.decode("ascii").strip()
    print(f"ES started as {state['es_container']}")

    print("creating stream ahead of time, so it is ready to populate with records")
    state["client"] = boto3.client(
        "kinesis",
        region_name="us-east-1",
        endpoint_url="http://localhost:6568",
        aws_access_key_id="foo",
        aws_secret_access_key="bar",
        verify=False,
    )
    state["client"].create_stream(
        StreamName="MetadataIsAvailable", ShardCount=1)
    time.sleep(3)
    print("created stream")

    es_create = subprocess.run(
        "FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_SERVICE_HOST=127.0.0.1 ELASTICSEARCH_SERVICE_PORT=9201  python create_index.py",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True
    )
    if es_create.returncode != 0:
        raise RuntimeError(f"Could not create elasticsearch index: {es_create.stdout}")
    
    print("created empty ES index")
    
    print("about to indexed test data set, from cache if possible")
    es_load = subprocess.run(
        "FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_SERVICE_HOST=127.0.0.1 ELASTICSEARCH_SERVICE_PORT=9201 python bulk_index.py --load_cache",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True
    )
    if es_load.returncode != 0:
        raise RuntimeError("Could not load elasticsearch: {es_load.stdout}")
        
    print("Done indexing test data set")

    return state


def tear_down_integration(state):
    """Tear down Elasticsearch once all tests have run."""
    _ = subprocess.run(

        f"docker rm -f {state['ls_container']}",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )

if __name__ == '__main__':
    setup_for_integration_test()
