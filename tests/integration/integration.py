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
    
    es_port = "9200"
    """ES Port outside of docker integration-test-elasticsearch container"""
    
    os.environ["ELASTICSEARCH_SERVICE_HOST"] = "localhost"
    os.environ["ELASTICSEARCH_SERVICE_PORT"] = es_port
    os.environ["ELASTICSEARCH_SERVICE_PORT_{es_port}_PROTO"] = "http"
    os.environ["ELASTICSEARCH_VERIFY"] = "false"

    print("pulling localstack image")
    subprocess.run(
        "docker pull atlassianlabs/localstack",
        shell=True, check=True
    )
    print("Building elasticsearch")
    es_build = subprocess.run(
        "docker build --file Dockerfile-elasticsearch --label arxiv/elasticsearch .",
        shell=True,check=True)

    print("Attempting to kill any old integration-test-elasticsearch")
    subprocess.run("docker kill integration-test-elasticsearch", shell=True)
    
    cmd = f"docker run -d --rm -p {es_port}:9200 " \
        "--name integration-test-elasticsearch arxiv/elasticsearch " \
        "--env http.host=0.0.0.0 --env transport.host=127.0.0.1"
    print(cmd)
    es_run = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            shell=True,
                            check=True)

    state["es_container"] = es_run.stdout.decode("ascii").strip()
    print(f"ES started as {state['es_container']}")

    print("About to create the index in ES.")
    cmd = f"ELASTICSEARCH_SERVICE_HOST=127.0.0.1 ELASTICSEARCH_SERVICE_PORT={es_port}  python create_index.py",
    print(cmd)
    es_create = subprocess.run(cmd,
                               check=True,
                               shell=True)   
    print("created empty ES index")
    
    print("About to indexed test data set, from cache if possible")
    cmd = f"ELASTICSEARCH_SERVICE_HOST=127.0.0.1 ELASTICSEARCH_SERVICE_PORT={es_port} python bulk_index.py",
    es_load = subprocess.run(cmd, shell=True, check=True )
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
