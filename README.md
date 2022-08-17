# docshots

Compare screenshots of Envoy (protodoc-generated API) docs.

For 2 versions of Envoy docs (stored in GCS) - eg a4d6e1f (before) and b9557aa (after) use like so:

```console

$ mkdir failed
$ docker build . -t scraper
$ docker run -v ${PWD}/failed:/failed scraper a4d6e1f b9557aa
```

Any pages that do not match will be output to the supplied `failed` directory.
