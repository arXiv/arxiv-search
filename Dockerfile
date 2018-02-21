# Run the Flask development server

FROM arxiv/base

# Add Python consumer and configuration.
ADD requirements.txt /opt/arxiv/
ADD app.py /opt/arxiv/
RUN pip install -U pip
RUN pip install -r /opt/arxiv/requirements.txt

ENV PATH "/opt/arxiv:${PATH}"

ADD schema /opt/arxiv/schema
ADD mappings /opt/arxiv/mappings
ADD search /opt/arxiv/search
ADD wsgi.py /opt/arxiv/
RUN pip install uwsgi

EXPOSE 8000

WORKDIR /opt/arxiv
#CMD /bin/bash
ENTRYPOINT ["/usr/bin/uwsgi"]
CMD ["--http-socket", ":8000", "-w wsgi", "-M", "-t 3000", "--manage-script-name", "--processes", "8", "--threads", "1", "--async", "100", "--ugreen", "--mount", "/search=wsgi.py"]
