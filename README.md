# arxiv-search

## Documentation

- OpenAPI Documentation: [``api/search.yaml``](api/search.yaml)
- JSON Schema: [``schema/``](schema)
- Elasticsearch mappings: [``mappings/``](mappings)


## Development quickstart

### Running Elasticsearch

```bash
docker build -t "arxivsearch_elasticsearch" -f ./Dockerfile-elasticsearch .
docker run -it -e "http.host=0.0.0.0" -e "transport.host=127.0.0.1" \
  -p 9200:9200 -p 9300:9300 \
  arxivsearch_elasticsearch
```

### Alternatively: Running Elasticsearch with Kibana
**TODO::** docker-compose version
```bash
docker-compose up
```
Kibana will be available at http://127.0.0.1.5601/

### Create & populate the index

```bash
pip install -r requirements.txt
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 python create_index.py
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 python populate_test_metadata.py
```

``populate_test_metadata.py`` without parameters populate the index with the
list of papers defined in ```tests/data/sample.json``. It take several minutes
to run. Individual paper IDs may be specified with the ``--paper_id``
parameter.

You'll need to do this any time you restart ES.

### Flask dev server

You can run the search app directly. Using virtualenv:

```bash
virtualenv ~/.venv/arxiv-search
source ~/.venv/arxiv-search/bin/activate
cd /wherever/you/put/arxiv-search
pip install -r requirements.txt
FLASK_APP=app.py FLASK_DEBUG=1 ELASTICSEARCH_HOST=127.0.0.1 flask run
```

This will monitor any of the Python bits for changes and restart the server.
Unfortunately static files and templates are not monitored, so you'll have to
manually restart to see those changes take effect.

## If all goes well...

http://127.0.0.1:5000/search/ should render the basic search page.

**NOTE:** not yet implemented!
http://127.0.0.1:5000/find?primary_archive.id=physics

```
{
  "results": {
    "count": 69,
    "results": [
      {
        "abs_categories": "physics.ins-det",
        "abstract": "We report on the design and commissioning of a new spectrometer for muon-spin relaxation/rotation studies installed at the Swiss Muon Source (S$\\mu$S) of the Paul Scherrer Institute (PSI, Switzerland). This new instrument is essentially a new design and replaces the old general-purpose surface-muon instrument (GPS) which has been for long the workhorse of the $\\mu$SR user facility at PSI. By making use of muon and positron detectors made of plastic scintillators read out by silicon photomultipliers (SiPMs), a time resolution of the complete instrument of about 160 ps (standard deviation) could be achieved. In addition, the absence of light guides, which are needed in traditionally built $\\mu$SR instrument to deliver the scintillation light to photomultiplier tubes located outside magnetic fields applied, allowed us to design a compact instrument with a detector set covering an increased solid angle compared to the old GPS.",
        "authors": [
          {
            "first_name": "Alex",
            "last_name": "Amato",
            "orcid": "0000-0001-9963-7498"
          }
        ],
        "comments": "11 pages, 11 figures",
        "date_created": "2017-10-02T03:03:55-0400",
        "date_modified": "2017-10-02T20:13:59-0400",
        "date_updated": "2017-10-02T20:13:59-0400",
        "doi": "10.1063/1.4986045",
        "is_current": true,
        "is_withdrawn": false,
        "journal_ref": "Review of Scientific Instruments 88, 093301 (2017)",
        "license": {
          "label": "arXiv.org perpetual, non-exclusive license to distribute this article",
          "uri": "http://arxiv.org/licenses/nonexclusive-distrib/1.0/"
        },
        "metadata_id": 2012294,
        "paper_id": "1705.10687",
        "paper_id_v": "1705.10687v2",
        "primary_archive": {
          "id": "physics",
          "name": "Physics"
        },
        "primary_category": {
          "id": "physics.ins-det",
          "name": "Instrumentation and Detectors"
        },
        "primary_group": {
          "id": "physics",
          "name": "Physics"
        },
        "score": 2.177422,
        "source": {
          "flags": "",
          "format": "pdftex",
          "size_bytes": 2613263
        },
        "submitter": {
          "email": "alex.amato@psi.ch",
          "is_author": true,
          "name": "Alex Amato",
          "orcid": "0000-0001-9963-7498"
        },
        "title": "The new versatile general purpose surface-muon instrument (GPS) based on silicon photomultipliers for ${\\mu}$SR measurements on a continuous-wave beam",
        "type": "arxiv",
        "version": 2
      },
      ...
   ]
}
```
