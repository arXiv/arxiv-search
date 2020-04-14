# Deployment Instructions for classic-api

To install `classic-api` to the development namespace in the kubernetes cluster:

```bash
helm install ./ --name=classic-api --set=image.tag=some_tag \
  --tiller-namespace=development --namespace=development  \
  --set=ingress.host=development.arxiv.org \
  --set=elasticsearch.host=foo.es.amazonaws.com \
  --set=elasticsearch.index=arxiv0.3
```

To delete the pod(s) associated with `classic-api`, run:

```bash
helm del --purge classic-api --tiller-namespace=development
```

Notes:
- `image.tag`: this refers to the tag in [dockerhub](https://hub.docker.com/repository/docker/arxiv/compiler-api)
- `elasticsearch.host`: this is the hostname of our Elasticsearch endpoint. We have provisioned it in AWS.
- `elasticsearch.index`: this is the index identifier. As of this writing, `arxiv0.3` is the index associated with development.
