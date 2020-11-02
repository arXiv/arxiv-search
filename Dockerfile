# arxiv/search
#
# Defines the runtime for the arXiv search service, which provides the main
# UIs (and, eventually, APIs) for search.

FROM arxiv/base:0.16.7

WORKDIR /opt/arxiv

# remove conflicting mariadb-libs from arxiv/base
RUN yum remove -y mariadb-libs

# Install MySQL.
RUN yum install -y which mysql mysql-devel
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
