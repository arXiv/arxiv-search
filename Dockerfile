# Run the Flask development server

FROM arxiv/base

# Add Python application and configuration.
ADD requirements/prod.txt /opt/arxiv/requirements.txt
ADD app.py /opt/arxiv/
RUN pip install -U pip
RUN pip install -r /opt/arxiv/requirements.txt

ENV PATH "/opt/arxiv:${PATH}"

ADD schema /opt/arxiv/schema
ADD mappings /opt/arxiv/mappings
ADD search /opt/arxiv/search
ADD wsgi.py /opt/arxiv/
RUN pip install uwsgi

ENV ELASTICSEARCH_SERVICE_HOST 127.0.0.1
ENV ELASTICSEARCH_SERVICE_PORT 9200
ENV ELASTICSEARCH_PORT_9200_PROTO http
ENV ELASTICSEARCH_INDEX arxiv
ENV ELASTICSEARCH_USER elastic
ENV ELASTICSEARCH_PASSWORD changeme
ENV METADATA_ENDPOINT https://arxiv.org/docmeta/

EXPOSE 8000

WORKDIR /opt/arxiv
#CMD /bin/bash
ENTRYPOINT ["/usr/bin/uwsgi"]
CMD ["--http-socket", ":8000", "-w wsgi", "-M", "-t 3000", "--manage-script-name", "--processes", "8", "--threads", "1", "--async", "100", "--ugreen", "--mount", "/search=wsgi.py"]
