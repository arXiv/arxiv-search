#!/bin/bash

echo "Starting agent"

# Since the MultiLangDaemon chokes on stdout/stderr from the Python
#  record processor, application log messages are piped to a logfile.

# Make sure that the logfile exists before we start.
touch ${LOGFILE}

PYPATH=$(pipenv --venv)

# Note conjoined ``tail -F ${LOGFILE}`` at the end; this ensures that app
#  log messages make it out to stdout safely, where they can be handled by the
#  Docker logs.
/usr/bin/java ${JAVA_FLAGS} -cp ${PYPATH}/lib/python3.6/site-packages/localstack/infra/amazon-kinesis-client/aws-java-sdk-sts.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/aws-java-sdk-dynamodb-1.11.115.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/jackson-dataformat-cbor-2.6.6.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/protobuf-java-2.6.1.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/jackson-databind-2.6.6.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/commons-codec-1.9.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/httpclient-4.5.2.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/commons-lang-2.6.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/jmespath-java-1.11.115.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/joda-time-2.8.1.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/aws-java-sdk-kinesis-1.11.115.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/commons-logging-1.1.3.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/guava-18.0.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/httpcore-4.4.4.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/aws-java-sdk-cloudwatch-1.11.115.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/ion-java-1.0.2.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/jackson-annotations-2.6.0.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/amazon-kinesis-client-1.7.5.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/aws-java-sdk-kms-1.11.115.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/jackson-core-2.6.6.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/aws-java-sdk-s3-1.11.115.jar:${PYPATH}/lib/python3.6/site-packages/amazon_kclpy/jars/aws-java-sdk-core-1.11.115.jar:/opt/arxiv:${PYPATH}/lib/python3.6/site-packages/localstack/utils/kinesis/java com.atlassian.KinesisStarter ${MODE}.properties & tail -F ${LOGFILE}
