"""
Notes on author name search tuning.

This is here for experimentation purposes only.
"""

import re
import time
from string import punctuation
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, SF
from elasticsearch_dsl.query import Range, Match, Bool
from elasticsearch_dsl.response import Response


mapping = """
{
  "settings": {
    "analysis": {
      "analyzer": {
        "simple": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase"
          ]
        },
        "folding": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "icu_folding",
            "lowercase",
            "german_normalization"
          ]
        }
      },
      "normalizer": {
        "simple": {
          "filter": [
            "lowercase"
          ]
        },
        "folding": {
          "filter": [
            "icu_folding",
            "lowercase"
          ]
        }
      }
    }
  },
  "mappings": {
    "document": {
      "dynamic": "false",
      "properties": {
        "authors": {
          "type": "nested",
          "properties": {
            "first_name": {
              "type": "text",
              "analyzer": "folding",
              "similarity": "classic",
              "fields": {
                "exact": {
                    "type": "keyword",
                    "normalizer": "folding"
                }
              }
            },
            "last_name": {
              "type": "text",
              "analyzer": "folding",
              "similarity": "classic",
              "fields": {
                "exact": {
                    "type": "keyword",
                    "normalizer": "folding"
                }
              }
            },
            "initials": {
              "type": "keyword",
              "normalizer": "simple",
              "fields": {
                "folded": {
                  "type": "keyword",
                  "normalizer": "folding"
                }
              }
            },
            "full_name": {
              "type": "text",
              "analyzer": "folding",
              "similarity": "classic",
              "fields": {
                "exact": {
                    "type": "keyword",
                    "normalizer": "folding"
                }
              }
            },
            "full_name_initialized": {
              "type": "text",
              "analyzer": "folding",
              "similarity": "classic",
              "fields": {
                "exact": {
                    "type": "keyword",
                    "normalizer": "folding"
                }
              }
            },
            "suffix": {
              "type": "keyword"
            },
            "author_id": {
              "type": "keyword"
            },
            "orcid": {
              "type": "keyword"
            },
            "affiliation": {
              "type": "text"
            }
          }
        }
      }
    }
  }
}
"""

docs = [
    {"id": 0, "authors": [{"first_name": "J. L.", "last_name": "Doe"}]},
    {"id": 1, "authors": [{"first_name": "JL", "last_name": "Doe"}]},
    {"id": 2, "authors": [{"first_name": "Jane", "last_name": "Doe"}]},
    {"id": 3, "authors": [{"first_name": "L Jane", "last_name": "Doe"}]},
    {"id": 4, "authors": [{"first_name": "John", "last_name": "Doe"}]},
    {"id": 5, "authors": [{"first_name": "James L.", "last_name": "Doe"}]},
    {"id": 6, "authors": [{"first_name": "L", "last_name": "Jane Doe"}]},
    {"id": 7, "authors": [{"first_name": "L", "last_name": "Doe"}]},
    {"id": 8, "authors": [{"first_name": "L", "last_name": "Jane"}]},
    {"id": 9, "authors": [{"first_name": "J", "last_name": "Doe"}]},
    {"id": 10, "authors": [{"first_name": "J.", "last_name": "Doe-Eberhard"}]},
    {"id": 11, "authors": [{"first_name": "Jane", "last_name": "Doe-Eberhard"}]},
    {"id": 20, "authors": [{"first_name": "Jane", "last_name": "Doe Eberhard"}]},
    {"id": 12, "authors": [{"first_name": "Jane", "last_name": "Eberhard"}]},
    {"id": 13, "authors": [{"first_name": "Jane", "last_name": "Dö"}]},
    {"id": 14, "authors": [{"first_name": "Jame", "last_name": "Doe"}]},
    {"id": 15, "authors": [{"first_name": "Jane", "last_name": "Doi"}]},

    {"id": 16, "authors": [{"first_name": "Chien Liang", "last_name": "Fok"}]},
    {"id": 17, "authors": [{"first_name": "Chien", "last_name": "Liang Fok"}]},
    {"id": 18, "authors": [{"first_name": "Liang Fok", "last_name": "Chien"}]},
    {"id": 19, "authors": [{"first_name": "C L", "last_name": "Fok"}]},
]


def _strip_punctuation(s: str) -> str:
    s = ''.join([c if c not in punctuation else " " for c in s])
    return re.sub(r'\s+', ' ', s)


def prepare(doc: dict):
    for author in doc['authors']:
        author['first_name'] = _strip_punctuation(author['first_name']).strip()
        author['full_name'] = re.sub(r'\s+', ' ', f"{author['first_name']} {author['last_name']}")
        author['initials'] = [pt[0] for pt in author['first_name'].split() if pt]
        # initials = ' '.join(author["initials"])
        name_parts = author['first_name'].split() + author['last_name'].split()
        author['full_name_initialized'] = ' '.join([part[0] for part in name_parts[:-1]] + [name_parts[-1]])


INDEX = 'test_authors'

es = Elasticsearch()

try:
    es.indices.create(INDEX, mapping)
except:
    pass

for doc in docs:
    prepare(doc)
    es.index(index=INDEX, doc_type='document', id=doc['id'], body=doc)


def author_search(qs: str):
    qs_parts = qs.split()
    qs_init = ' '.join([part[0] for part in qs_parts[:-1]] + [qs_parts[-1]])

    query = Q("nested", path="authors", query=(
        Q('match', **{'authors__full_name__exact': {'query': qs, 'boost': 10}})
        | Q('match_phrase', **{'authors__full_name': {'query': qs, 'boost': 9}})
        | Q('match', **{'authors__full_name': {'query': qs, 'boost': 8, 'operator': 'and'}})
        | Q('match', **{'authors__full_name_initialized__exact': {'query': qs_init, 'boost': 5}})
        | Q('match_phrase', **{'authors__full_name_initialized': {'query': qs_init, 'boost': 4}})
    ))
    qs_first = ' '.join(qs.split()[:-1])
    qs_init_first = ' '.join(qs_init.split()[:-1])
    query = Q(
        'function_score', query=query, score_mode="sum", boost=1, boost_mode='multiply', functions=[

            SF({'weight': 25, 'filter': Q("nested", path="authors", query=Q('match', **{'authors__full_name': qs}))}),
            SF({'weight': 20, 'filter': Q("nested", path="authors", query=Q('match', **{'authors__full_name_initialized': qs}))}),
            SF({'weight': 15, 'filter': Q("nested", path="authors", query=Q('match', **{'authors__last_name': qs.split()[-1]}))}),

            SF({'weight': 10, 'filter': Q("nested", path="authors", query=Q("match", **{"authors__first_name__exact": qs_first}))}),
            SF({'weight': 8, 'filter': Q("nested", path="authors", query=Q("match", **{"authors__first_name__exact": qs_init_first}))}),

            SF({'weight': 10, 'filter': Q("nested", path="authors", query=Q("match_phrase", **{"authors__first_name": qs_first}))}),
            SF({'weight': 8, 'filter': Q("nested", path="authors", query=Q("match_phrase", **{"authors__first_name": qs_init_first}))}),
            SF({'weight': 1, 'filter': Q("nested", path="authors", query=Q("match", **{"authors__first_name": qs_first}))}),
            SF({'weight': 1, 'filter': Q("nested", path="authors", query=Q("match", **{"authors__first_name": qs_init_first}))}),

            SF({'weight': 2, 'filter': Q("nested", path="authors", query=Q("match", **{"authors__initials": qs_init_first.lower()}))}),
        ]
    )
    search = Search(using=es, index=INDEX)
    return search.query(query)[:50].execute()

time.sleep(2)

test_cases = [
    ('Jane Doe', [
        (0, 3),
        (1, None),
        (2, 1),
        (3, 2),
        (4, None),
        (5, None),
        (6, 2),
        (7, None),
        (8, None),
        (9, 3),
        (10, 4),
        (11, 2),
        (12, None),
        (13, 2),
        (14, None),
        (15, None),
        (20, 2)
    ]),
    ('J Doe', [
        (0, 2),
        (1, 3),
        (2, 3),
        (3, 4),
        (4, 3),
        (5, 3),
        (6, None),
        (7, None),
        (8, None),
        (9, 1),
        (10, 2),
        (11, 3),
        (12, None),
        (13, 3),
        (14, 3),
        (15, None)
    ]),
    ('Chien Liang Fok', [])
]

for qs, ranks in test_cases:
    print('--'*80)
    print(qs)
    print('--'*80)
    failed = 0.
    ranks = dict(ranks)
    results = author_search(qs)
    order = []
    print('ID'.ljust(4), 'Rank'.ljust(6), 'ES Score'.ljust(10), 'Document')
    for result in results:
        rank = ranks.get(result['id'], None)
        print(str(result['id']).ljust(4), str(rank).ljust(6), str(result.meta.score).ljust(10), result['authors'])
        if rank is not None and len(order) > 0:
            try:
                assert order[-1] is not None
                assert rank >= order[-1]
            except AssertionError:
                failed += 1.

        order.append(rank)
    print('\n', 'Score:', 1. - (failed/len(order)))

# es.indices.delete(INDEX)
