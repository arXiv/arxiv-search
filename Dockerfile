# arxiv/search
#
# Defines the runtime for the arXiv search service, which provides the main
# UIs (and, eventually, APIs) for search.

FROM arxiv/base

WORKDIR /opt/arxiv

# Add Python application and configuration.
ADD requirements/prod.txt /opt/arxiv/requirements.txt
ADD app.py /opt/arxiv/
ADD Pipfile /opt/arxiv/
ADD Pipfile.lock /opt/arxiv/
RUN pip install -U pip pipenv
RUN pipenv install

ENV PATH "/opt/arxiv:${PATH}"

ADD schema /opt/arxiv/schema
ADD mappings /opt/arxiv/mappings
ADD search /opt/arxiv/search
ADD wsgi.py /opt/arxiv/
RUN pip install uwsgi

ADD bin/start_search.sh /opt/arxiv/
RUN chmod +x /opt/arxiv/start_search.sh

ENV LC_ALL en_US.utf8
ENV LANG en_US.utf8
ENV LOGLEVEL 40
ENV FLASK_DEBUG 1
ENV FLASK_APP /opt/arxiv/app.py

ENV ELASTICSEARCH_SERVICE_HOST 127.0.0.1
ENV ELASTICSEARCH_SERVICE_PORT 9200
ENV ELASTICSEARCH_PORT_9200_PROTO http
ENV ELASTICSEARCH_INDEX arxiv
ENV ELASTICSEARCH_USER elastic
ENV ELASTICSEARCH_PASSWORD changeme
ENV METADATA_ENDPOINT https://arxiv.org/docmeta/

EXPOSE 8000

#CMD /bin/bash
ENTRYPOINT ["/opt/arxiv/start_search.sh"]
CMD ["--http-socket", ":8000", \
     "-M", \
     "-t 3000", \
     "--manage-script-name", \
     "--processes", "8", \
     "--threads", "1", \
     "--async", "100", \
     "--ugreen", \
     "--mount", "/search=wsgi.py", \
     "--logformat", "%(addr) %(addr) - %(user_id)|%(session_id) [%(rtime)] [%(uagent)] \"%(method) %(uri) %(proto)\" %(status) %(size) %(micros) %(ttfb)"]
