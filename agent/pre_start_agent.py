"""Creates the Kinesis stream if it does not already exist."""

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
import os
from search.factory import create_ui_web_app
from search.context import get_application_config
import sys


if __name__ == '__main__':
    app = create_ui_web_app()
    app.app_context().push()
    config = get_application_config()

    endpoint = config.get('KINESIS_ENDPOINT')
    region = config.get('AWS_REGION', 'us-east-1')
    access_key = config.get('AWS_ACCESS_KEY_ID', "")
    aws_secret = config.get('AWS_SECRET_ACCESS_KEY', "")
    verify = config.get('KINESIS_VERIFY') == 'true'
    stream_name = config.get('KINESIS_STREAM', 'MetadataIsAvailable')

    config = Config(read_timeout=5, connect_timeout=5)
    client = boto3.client('kinesis', region_name=region, endpoint_url=endpoint,
                          aws_access_key_id=access_key,
                          aws_secret_access_key=aws_secret,
                          verify=verify, config=config)
    try:
        client.describe_stream(StreamName=stream_name)
    except ClientError:
        client.create_stream(StreamName=stream_name, ShardCount=1)
