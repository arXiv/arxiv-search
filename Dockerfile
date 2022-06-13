# arxiv/search
#
# Defines the runtime for the arXiv search service, which provides the main
# UIs (and, eventually, APIs) for search.

FROM arxiv/base:0.16.5 AS search_web_app

WORKDIR /opt/arxiv

# Install MySQL.
RUN yum install -y which  mysql-devel
RUN pip install uwsgi

# Add Python application and configuration.
ADD app.py /opt/arxiv/
ADD Pipfile /opt/arxiv/
ADD Pipfile.lock /opt/arxiv/
RUN pip install -U pip pipenv
RUN pipenv install

ENV PATH "/opt/arxiv:${PATH}"

ADD schema /opt/arxiv/schema
ADD mappings /opt/arxiv/mappings
ADD search /opt/arxiv/search
ADD wsgi.py uwsgi.ini /opt/arxiv/


ADD bin/start_search.sh /opt/arxiv/
RUN chmod +x /opt/arxiv/start_search.sh

ENV LC_ALL en_US.utf8
ENV LANG en_US.utf8
ENV LOGLEVEL 40
ENV FLASK_DEBUG 1
ENV FLASK_APP /opt/arxiv/app.py

ENV ELASTICSEARCH_SERVICE_HOST 127.0.0.1
ENV ELASTICSEARCH_SERVICE_PORT 9200
ENV ELASTICSEARCH_SERVICE_PORT_9200_PROTO http
ENV ELASTICSEARCH_PASSWORD changeme
ENV METADATA_ENDPOINT https://arxiv.org/docmeta_bulk/

EXPOSE 8000
ENTRYPOINT ["pipenv", "run"]
CMD ["uwsgi", "--ini", "/opt/arxiv/uwsgi.ini"]


##############################
# Stage for integration tests
##############################
FROM search_web_app AS search_web_app_test

ENV WITH_INTEGRATION True

ADD create_index.py /opt/arxiv/
ADD bulk_index.py /opt/arxiv/
ADD integration_test.sh /opt/arxiv/
ADD tests /opt/arxiv/tests

RUN yum install -y httpie
#RUN pipenv install -d

CMD ["http", "https://arxiv.org/docmeta_bulk?id=astro-ph/0311033&id=0809.2702&id=0803.3453&id=0710.2374&id=0704.3437&id=astro-ph/0611319&id=astro-ph/0301161&id=astro-ph/0510845"]
#CMD ["/bin/bash", "./integration_test.sh"]
