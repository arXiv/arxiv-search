# arxiv-search

## Development quickstart

A ``docker-compose.yml`` configuration is included in the root of this
repository. It will start elasticsearch, using data in ``tests/data/es``,
and the search application.

```bash
docker-compose build
docker-compose up
```

The build step will take a little while to complete the first time around.

Unfortunately, file monitoring is somewhat broken on OSX/Docker, so you'll have
to stop (CTRL-C) and re-start (``docker-compose up``) for changes to be
reflected.

## Alternatively

If you want to start up ES outside of the compose context, you can
use:

```bash
docker run -p 9200:9200 \
    -e "http.host=0.0.0.0" \
    -e "transport.host=127.0.0.1" \
    -v "$PWD/tests/data/es:/usr/share/elasticsearch/data" \
    docker.elastic.co/elasticsearch/elasticsearch:5.5.3
```

You can run the search app directly. Using virtualenv:

```bash
virtualenv ~/.venv/arxiv-search
source ~/.venv/arxiv-search/bin/activate
cd /wherever/you/put/arxiv-search
pip install -r requirements.txt
FLASK_APP=app.py FLASK_DEBUG=1 flask run
```

This will monitor any of the Python bits for changes and restart the server.
Unfortunately static files and templates are not monitored, so you'll have to
manually restart to see those changes take effect.

## If all goes well...

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
