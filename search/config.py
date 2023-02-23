"""
Flask configuration.

Docstrings are from the `Flask configuration documentation
<http://flask.pocoo.org/docs/0.12/config/>`_.
"""
import os

APP_VERSION = "0.5.6"
"""The application version """

ON = "yes"
OFF = "no"

DEBUG = os.environ.get("DEBUG") == ON
"""enable/disable debug mode"""

TESTING = os.environ.get("TESTING") == ON
"""enable/disable testing mode"""

PROPAGATE_EXCEPTIONS = (
    True if os.environ.get("PROPAGATE_EXCEPTIONS") == ON else None
)
"""
explicitly enable or disable the propagation of exceptions. If not set or
explicitly set to None this is implicitly true if either TESTING or DEBUG is
true.
"""

PRESERVE_CONTEXT_ON_EXCEPTION = (
    True if os.environ.get("PRESERVE_CONTEXT_ON_EXCEPTION") == ON else None
)
"""
By default if the application is in debug mode the request context is not
popped on exceptions to enable debuggers to introspect the data. This can be
disabled by this key. You can also use this setting to force-enable it for non
debug execution which might be useful to debug production applications (but
also very risky).
"""


USE_X_SENDFILE = os.environ.get("USE_X_SENDFILE") == ON
"""Enable/disable x-sendfile"""

LOGGER_NAME = os.environ.get("LOGGER_NAME", "search")
"""The name of the logger."""

LOGGER_HANDLER_POLICY = os.environ.get("LOGGER_HANDLER_POLICY", "debug")
"""
the policy of the default logging handler. The default is 'always' which means
that the default logging handler is always active. 'debug' will only activate
logging in debug mode, 'production' will only log in production and 'never'
disables it entirely.
"""

SERVER_NAME = os.environ.get("SEARCH_SERVER_NAME", None)
"""
the name and port number of the server. Required for subdomain support
(e.g.: 'myapp.dev:5000') Note that localhost does not support subdomains so
setting this to 'localhost' does not help. Setting a SERVER_NAME also by
default enables URL generation without a request context but with an
application context.
"""

APPLICATION_ROOT = os.environ.get("APPLICATION_ROOT", "/")
"""
If the application does not occupy a whole domain or subdomain this can be set
to the path where the application is configured to live. This is for session
cookie as path value. If domains are used, this should be None.
"""

URL_PREFIX = os.environ.get("URL_PREFIX", "/")
"""
Pass this to blueprint in ./search/routes/ui.py.

The APPLICATION_ROOT above seems to be used in ./config/uwsgi*.ini
Which is probably also different from the wsgiscript line in arxiv-httpd.
"""


MAX_CONTENT_LENGTH = os.environ.get("MAX_CONTENT_LENGTH", None)
"""
If set to a value in bytes, Flask will reject incoming requests with a content
length greater than this by returning a 413 status code.
"""

SEND_FILE_MAX_AGE_DEFAULT = int(
    os.environ.get("SEND_FILE_MAX_AGE_DEFAULT", 43200)
)
"""
Default cache control max age to use with send_static_file() (the default
static file handler) and send_file(), as datetime.timedelta or as seconds.
Override this value on a per-file basis using the get_send_file_max_age() hook
on Flask or Blueprint, respectively. Defaults to 43200 (12 hours).
"""

TRAP_HTTP_EXCEPTIONS = os.environ.get("TRAP_HTTP_EXCEPTIONS") == ON
"""
If this is set to True Flask will not execute the error handlers of HTTP
exceptions but instead treat the exception like any other and bubble it through
the exception stack. This is helpful for hairy debugging situations where you
have to find out where an HTTP exception is coming from.
"""

TRAP_BAD_REQUEST_ERRORS = os.environ.get("TRAP_BAD_REQUEST_ERRORS") == ON
"""
Werkzeug's internal data structures that deal with request specific data will
raise special key errors that are also bad request exceptions. Likewise many
operations can implicitly fail with a BadRequest exception for consistency.
Since it’s nice for debugging to know why exactly it failed this flag can be
used to debug those situations. If this config is set to True you will get a
regular traceback instead.
"""

PREFERRED_URL_SCHEME = os.environ.get("PREFERRED_URL_SCHEME", "http")
"""
The URL scheme that should be used for URL generation if no URL scheme is
available. This defaults to http.
"""

JSON_AS_ASCII = os.environ.get("JSON_AS_ASCII") == ON
"""
By default Flask serialize object to ascii-encoded JSON. If this is set to
False Flask will not encode to ASCII and output strings as-is and return
unicode strings. jsonify will automatically encode it in utf-8 then for
transport for instance.
"""

JSON_SORT_KEYS = os.environ.get("JSON_AS_ASCII") != OFF
"""
By default Flask will serialize JSON objects in a way that the keys are
ordered. This is done in order to ensure that independent of the hash seed of
the dictionary the return value will be consistent to not trash external HTTP
caches. You can override the default behavior by changing this variable.
This is not recommended but might give you a performance improvement on the
cost of cacheability.
"""

JSONIFY_PRETTYPRINT_REGULAR = os.environ.get("JSON_AS_ASCII") != OFF
"""
If this is set to True (the default) jsonify responses will be pretty printed
if they are not requested by an XMLHttpRequest object (controlled by the
X-Requested-With header).
"""

JSONIFY_MIMETYPE = os.environ.get("JSONIFY_MIMETYPE", "application/json")
"""
MIME type used for jsonify responses.
"""

TEMPLATES_AUTO_RELOAD = os.environ.get("TEMPLATES_AUTO_RELOAD") == ON
"""
Whether to check for modifications of the template source and reload it
automatically. By default the value is None which means that Flask checks
original file only in debug mode.
"""

EXPLAIN_TEMPLATE_LOADING = os.environ.get("EXPLAIN_TEMPLATE_LOADING") == ON
"""
If this is enabled then every attempt to load a template will write an info
message to the logger explaining the attempts to locate the template. This can
be useful to figure out why templates cannot be found or wrong templates appear
to be loaded.
"""

# AWS credentials.
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "nope")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "nope")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

LOGFILE = os.environ.get("LOGFILE")
LOGLEVEL = os.environ.get("LOGLEVEL", 40)
"""
Log level for search service.

See `<https://docs.python.org/3/library/logging.html#logging-levels>`_ .
"""

ELASTICSEARCH_SERVICE_HOST = os.environ.get(
    "ELASTICSEARCH_SERVICE_HOST", "localhost"
)
ELASTICSEARCH_SERVICE_PORT = os.environ.get(
    "ELASTICSEARCH_SERVICE_PORT", "9200"
)
_proto_key = "ELASTICSEARCH_SERVICE_PORT_%s_PROTO" % ELASTICSEARCH_SERVICE_PORT
locals()[_proto_key] = os.environ.get(_proto_key, "http")

ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "arxiv")
ELASTICSEARCH_USER = os.environ.get("ELASTICSEARCH_USER", None)
ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD", None)
ELASTICSEARCH_VERIFY = os.environ.get("ELASTICSEARCH_VERIFY", "true")
"""Indicates whether SSL certificate verification for ES should be enforced."""


METADATA_ENDPOINT = os.environ.get("METADATA_ENDPOINT", "https://arxiv.org/")
"""
Location of endpoint(s) for metadata retrieval.

Multiple endpoints may be provided with comma delimitation.
"""

METADATA_CACHE_DIR = os.environ.get("METADATA_CACHE_DIR")
"""Cache directory for metadata documents."""

METADATA_VERIFY_CERT = os.environ.get("METADATA_VERIFY_CERT", "True")
"""If ``False``, SSL certificate verification will be disabled."""

#This is currently not in use. Currently arxiv-search does not index the full text of articles.
FULLTEXT_ENDPOINT = os.environ.get(
    "FULLTEXT_ENDPOINT", "https://fulltext.arxiv.org/fulltext/"
)

# Settings for the indexing agent.
KINESIS_ENDPOINT = os.environ.get("KINESIS_ENDPOINT")
"""Can be used to set an alternate endpoint, e.g. for testing."""

KINESIS_VERIFY = os.environ.get("KINESIS_VERIFY", "true")
"""Indicates whether SSL certificate verification should be enforced."""

KINESIS_STREAM = os.environ.get("KINESIS_STREAM", "MetadataIsAvailable")
"""Name of the stream to which the indexing agent subscribes."""

KINESIS_SHARD_ID = os.environ.get("KINESIS_SHARD_ID", "0")

KINESIS_CHECKPOINT_VOLUME = os.environ.get("KINESIS_CHECKPOINT_VOLUME", "/tmp")

KINESIS_START_TYPE = os.environ.get("KINESIS_START_TYPE", "AT_TIMESTAMP")
KINESIS_START_AT = os.environ.get("KINESIS_START_AT")

KINESIS_SLEEP = os.environ.get("KINESIS_SLEEP", "0.1")
"""Amount of time to wait before moving on to the next record."""


"""
Flask-S3 plugin settings.

See `<https://flask-s3.readthedocs.io/en/latest/>`_.
"""
FLASKS3_BUCKET_NAME = os.environ.get("FLASKS3_BUCKET_NAME", "some_bucket")
FLASKS3_CDN_DOMAIN = os.environ.get("FLASKS3_CDN_DOMAIN", "static.arxiv.org")
FLASKS3_USE_HTTPS = os.environ.get("FLASKS3_USE_HTTPS", 1)
FLASKS3_FORCE_MIMETYPE = os.environ.get("FLASKS3_FORCE_MIMETYPE", 1)
FLASKS3_ACTIVE = os.environ.get("FLASKS3_ACTIVE", 0)

# Settings for display of release information
RELEASE_NOTES_URL = "https://github.com/arXiv/arxiv-search/releases"
RELEASE_NOTES_TEXT = "Search v0.5.6 released 2020-02-24"


EXTERNAL_URL_SCHEME = os.environ.get("EXTERNAL_URL_SCHEME", "https")
BASE_SERVER = os.environ.get("BASE_SERVER", "arxiv.org")

URLS = [
    ("pdf", "/pdf/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("pdf_by_id", "/pdf/<arxiv:paper_id>", BASE_SERVER),
    ("abs", "/abs/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("abs_by_id", "/abs/<arxiv:paper_id>", BASE_SERVER),
    ("pdfonly", "/pdf/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("pdfonly_by_id", "/pdf/<arxiv:paper_id>", BASE_SERVER),
    ("dvi", "/dvi/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("dvi_by_id", "/dvi/<arxiv:paper_id>", BASE_SERVER),
    ("html", "/html/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("html_by_id", "/html/<arxiv:paper_id>", BASE_SERVER),
    ("ps", "/ps/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("ps_by_id", "/ps/<arxiv:paper_id>", BASE_SERVER),
    ("source", "/e-print/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("source_by_id", "/e-print/<arxiv:paper_id>", BASE_SERVER),
    ("other", "/format/<arxiv:paper_id>v<string:version>", BASE_SERVER),
    ("other_by_id", "/format/<arxiv:paper_id>", BASE_SERVER),
]

JWT_SECRET = os.environ.get("JWT_SECRET", "foosecret")

# TODO: one place to set the version, update release notes text, JIRA issue
# collector, etc.
