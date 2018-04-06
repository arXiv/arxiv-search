"""Creates the Kinesis stream if it does not already exist."""

import boto3
from botocore.exceptions import ClientError
from botocore.vendored.requests.exceptions import ConnectionError
from botocore.client import Config
import os
from search.factory import create_ui_web_app
from search.context import get_application_config
import sys
import time

from arxiv.base import logging
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    logger.debug('Pre-start routine for indexing agent')
    app = create_ui_web_app()
    app.app_context().push()
    config = get_application_config()
    logger.debug('App context initialized')

    endpoint = config.get('KINESIS_ENDPOINT')
    region = config.get('AWS_REGION', 'us-east-1')
    access_key = config.get('AWS_ACCESS_KEY_ID', "")
    aws_secret = config.get('AWS_SECRET_ACCESS_KEY', "")
    verify = config.get('KINESIS_VERIFY') == 'true'
    stream_name = config.get('KINESIS_STREAM', 'MetadataIsAvailable')
    logger.debug(f'Kinesis endpoint: {endpoint}')

    config = Config(read_timeout=5, connect_timeout=5)
    client = boto3.client(
        'kinesis',
        region_name=region,
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=aws_secret,
        verify=verify,
        config=config
    )
    logger.debug('Got Kinesis client.')

    logger.debug('Waiting for Kinesis to be available...')
    start_time = time.time()
    while True:
        duration = time.time() - start_time
        logger.debug(f'Waiting for Kinesis to be available... {duration}s')
        if duration > 60:
            raise RuntimeError(
                'Failed to connect to Kinesis in {duration} seconds'
            )
        try:
            client.describe_stream(StreamName=stream_name)
            logger.debug(f'Connected to stream {stream_name}')
            break
        except ConnectionError:
            time.sleep(duration)    # Back off.
        except ClientError:
            logger.debug('Stream does not exist; creating {stream_name}')
            client.create_stream(StreamName=stream_name, ShardCount=1)
            break
    logger.debug('Done')
