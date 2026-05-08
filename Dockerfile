ARG GRAPHDB_VERSION=11.3.2
FROM ontotext/graphdb:${GRAPHDB_VERSION}

ENV GDB_JAVA_OPTS="-Xms1g -Xmx4g"
ENV graphdb.workbench.importDirectory="/opt/graphdb/home/graphdb-import"
ENV graphdb.workbench.maxUploadSize="2147483648"

EXPOSE 7200

VOLUME ["/opt/graphdb/home", "/opt/graphdb/home/graphdb-import"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
  CMD curl -fsS -H "Accept: text/html" http://127.0.0.1:7200/ >/dev/null || exit 1
