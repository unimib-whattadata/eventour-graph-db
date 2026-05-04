# Deploy su Coolify

Questa repository e pronta per un deploy Docker Compose su Coolify usando il file `docker-compose.yml` di root.

## 1. Crea la risorsa

1. In Coolify crea una nuova **Resource**.
2. Scegli **Application** da repository Git.
3. Collega la repository:

   ```text
   https://github.com/unimib-whattadata/eventour-graph-db.git
   ```

4. Branch: `main`.
5. Build pack / deploy type: **Docker Compose**.
6. Compose file: `docker-compose.yml`.

Coolify usa il compose come sorgente principale della configurazione. Le variabili presenti nel file vengono mostrate nella UI e possono essere modificate da li.

## 2. Configura dominio e porta

Il servizio GraphDB ascolta sulla porta container `7200`.

Nel servizio `graphdb`, imposta il dominio includendo la porta interna:

```text
https://graphdb.tuo-dominio.it:7200
```

Coolify usera quel `:7200` per capire verso quale porta del container fare proxy; l'utente finale aprira comunque il normale URL HTTPS.

Non e necessario esporre una porta host con `ports:` in produzione. Il compose usa `expose: 7200`, cosi il servizio resta dietro al proxy di Coolify.

## 3. Variabili consigliate

Coolify rilevera queste variabili dal compose:

```env
GRAPHDB_VERSION=11.3.2
GDB_JAVA_OPTS=-Xms1g -Xmx4g
GRAPHDB_WORKBENCH_MAX_UPLOAD_SIZE=2147483648
```

Per import grandi puoi aumentare la heap Java, se il server ha RAM sufficiente:

```env
GDB_JAVA_OPTS=-Xms2g -Xmx6g
```

`GRAPHDB_WORKBENCH_MAX_UPLOAD_SIZE=2147483648` corrisponde a 2 GiB.

## 4. Storage persistente

Il compose definisce due volumi:

```yaml
graphdb_home
graphdb_import
```

`graphdb_home` contiene dati, repository, impostazioni e licenza caricata da Workbench. Deve restare persistente tra redeploy.

`graphdb_import` e montato in:

```text
/opt/graphdb/home/graphdb-import
```

Serve per import server-side da **Import > Server files**.

## 5. Licenza GraphDB

GraphDB 11 richiede una licenza.

Il modo piu semplice su Coolify:

1. fai il primo deploy;
2. apri il Workbench dal dominio configurato;
3. vai in **Setup > License > Set new license**;
4. carica la licenza;
5. riavvia la risorsa se GraphDB lo richiede.

La licenza resta nel volume `graphdb_home`, quindi sopravvive ai redeploy.

In alternativa, puoi montare un file `graphdb.license` nel percorso:

```text
/opt/graphdb/home/work/graphdb.license
```

Non committare mai la licenza nel repository.

## 6. Sicurezza

Evita di lasciare il Workbench pubblico senza protezione.

Opzioni consigliate:

- abilita la sicurezza/autenticazione dentro GraphDB;
- oppure proteggi il dominio in Coolify con Basic Auth, Authentik, Cloudflare Access o una rete privata.

## 7. Import del dataset

Per il file `eventour_final_kg_milan.nt`:

- evita l'upload browser da **Import > User data**: il file e grande e puo essere interrotto dal proxy prima di arrivare a GraphDB;
- carica il file nel volume `graphdb_import` e poi usa **Import > Server files**.

### Upload consigliato via SSH

Dal tuo computer, copia il file sul server Coolify:

```bash
scp eventour_final_kg_milan.nt root@IP_DEL_SERVER:/tmp/eventour_final_kg_milan.nt
```

Sul server, trova il container GraphDB:

```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | grep graphdb
```

Copia il file dentro la cartella import montata nel container:

```bash
docker cp /tmp/eventour_final_kg_milan.nt NOME_CONTAINER:/opt/graphdb/home/graphdb-import/eventour_final_kg_milan.nt
```

Poi apri il Workbench e importa da:

```text
Import > Server files > eventour_final_kg_milan.nt > Import
```

Se il file e disponibile da un URL scaricabile dal server, puoi anche aprire il terminale del container in Coolify e scaricarlo direttamente:

```bash
curl -L -o /opt/graphdb/home/graphdb-import/eventour_final_kg_milan.nt "URL_DEL_FILE"
```

oppure:

```bash
wget -O /opt/graphdb/home/graphdb-import/eventour_final_kg_milan.nt "URL_DEL_FILE"
```

Configurazione import consigliata:

```text
Target graph: Named graph
Named graph IRI: http://eventour.unimib.it/graph/milan
Base IRI: http://eventour.unimib.it/
Stop on error: enabled
Preserve BNode IDs: disabled
Datatype validation: disabled
Language validation: enabled
Force serial pipeline: disabled
```

Query di verifica:

```sparql
SELECT (COUNT(*) AS ?triples)
WHERE {
  GRAPH <http://eventour.unimib.it/graph/milan> {
    ?s ?p ?o .
  }
}
```

## 8. URL per applicazioni esterne

Endpoint SPARQL pubblico:

```text
https://graphdb.tuo-dominio.it/repositories/eventour
```

Se un'altra applicazione vive nello stesso stack Docker Compose, puo usare:

```text
http://graphdb:7200/repositories/eventour
```
