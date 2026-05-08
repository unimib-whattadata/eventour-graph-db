# Eventour GraphDB

Progetto Docker minimo per avviare [GraphDB](https://graphdb.ontotext.com/), caricare file RDF `.nt` e interrogare il repository con SPARQL.

## Verifica formato `.nt`

Si, `.nt` e un'estensione supportata. GraphDB documenta il formato **N-Triples** con MIME type `application/n-triples` / `text/plain` e file extension `.nt`: <https://graphdb.ontotext.com/documentation/11.3/rdf-formats.html#n-triples>.

Nota pratica: N-Triples non contiene namespace e non supporta named graph nel file stesso. Se vuoi importare tutto in un named graph, puoi sceglierlo nelle impostazioni di import del Workbench.

## Avvio

Requisiti: Docker Desktop o Docker Engine con Docker Compose.

Per avvio locale usa il compose di produzione piu l'override locale:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

Controlla i log:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml logs -f graphdb
```

Quando il server e pronto, apri:

```text
http://localhost:7200
```

Per spegnere:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml down
```

I dati GraphDB sono salvati nel volume Docker `eventour-graphdb_graphdb_home`, quindi sopravvivono al riavvio del container.

## Deploy su Coolify

Il file `docker-compose.yml` di root e pensato anche per produzione/Coolify:

- usa l'immagine ufficiale `ontotext/graphdb`;
- espone internamente la porta container `7200`;
- salva i dati in volumi persistenti `graphdb_home` e `graphdb_import`;
- include un healthcheck compatibile con GraphDB e Coolify;
- non pubblica porte host direttamente, lasciando il routing al proxy di Coolify.

Guida passo passo: [docs/coolify.md](docs/coolify.md).

In Coolify configura la risorsa come **Docker Compose** e usa:

```text
Compose file: docker-compose.yml
Service: graphdb
Porta container: 7200
Dominio esempio: https://graphdb.tuo-dominio.it:7200
```

Per GraphDB 11 ricordati di caricare la licenza dal Workbench in **Setup > License > Set new license** dopo il primo deploy, oppure di montare il file licenza nel volume persistente. Non committare mai la licenza nel repository.

## Creare il repository

1. Apri `http://localhost:7200`.
2. Vai in **Setup > Repositories**.
3. Clicca **Create new repository**.
4. Seleziona **GraphDB repository**.
5. Inserisci come **Repository ID**:

   ```text
   eventour
   ```

6. Lascia le altre impostazioni di default, a meno che tu non abbia requisiti specifici.
7. Clicca **Create**.
8. Se non viene connesso automaticamente, usa il menu in alto a destra o l'icona di connessione nella lista repository e seleziona `eventour`.

La procedura via Workbench e quella consigliata da GraphDB per il primo repository: <https://graphdb.ontotext.com/documentation/11.3/create-your-first-repository.html>.

## Caricare un file `.nt` dall'interfaccia

Hai due strade.

### Opzione A: upload dal browser

Usala per file piccoli o medi. In questo progetto il limite di upload del Workbench e impostato a 2 GiB con `graphdb.workbench.maxUploadSize=2147483648`.

Su server/Coolify evita questa strada per dataset grandi: il proxy puo interrompere la request multipart prima che GraphDB finisca di riceverla. Per file grandi usa **Import > Server files** come descritto nella guida Coolify.

1. Apri `http://localhost:7200`.
2. Seleziona il repository `eventour`.
3. Vai in **Import > User data**.
4. Clicca **Upload RDF files**.
5. Scegli il tuo file `.nt`.
6. Clicca **Import** sulla riga del file.
7. Nelle impostazioni:
   - **Base IRI**: puoi lasciarlo vuoto se il file usa solo IRI assoluti, come di solito succede nei `.nt`.
   - **Target graphs**: scegli **The default graph** oppure **Named graph** se vuoi isolare il dataset in un graph specifico.
8. Clicca **Import** e aspetta il completamento del job.

### Opzione B: file montato nel container

Usala per file grandi. Il compose monta la cartella locale `./import` dentro GraphDB come cartella di import server-side.

1. Copia il file nella cartella:

   ```bash
   cp /percorso/al/tuo/file.nt ./import/
   ```

2. Apri `http://localhost:7200`.
3. Seleziona il repository `eventour`.
4. Vai in **Import > Server files**.
5. Trova il file `.nt`.
6. Clicca **Import**.
7. Scegli default graph o named graph nelle impostazioni e conferma.

GraphDB documenta i server files come metodo adatto a file di dimensioni arbitrarie, configurabile con `graphdb.workbench.importDirectory`: <https://graphdb.ontotext.com/documentation/11.1/loading-data-using-the-workbench.html#importing-server-files>.

## Fare query SPARQL dal Workbench

1. Apri `http://localhost:7200`.
2. Seleziona il repository `eventour`.
3. Vai in **SPARQL**.
4. Incolla una query, per esempio:

   ```sparql
   SELECT ?s ?p ?o
   WHERE {
     ?s ?p ?o .
   }
   LIMIT 25
   ```

5. Clicca **Run**.

## Fare query SPARQL da terminale

Esempio con lo script incluso:

```bash
./scripts/query.sh queries/example.rq
```

Equivalente con `curl`:

```bash
curl \
  -H "Accept: application/sparql-results+json" \
  --data-urlencode "query@queries/example.rq" \
  http://localhost:7200/repositories/eventour
```

GraphDB espone un endpoint SPARQL per ogni repository nel formato `http://localhost:7200/repositories/<repo-id>`: <https://graphdb.ontotext.com/documentation/11.3/rdf4j-rest-api.html#using-the-rdf4j-rest-api-s-sparql-endpoints>.

## Caricare `.nt` da terminale

Dopo aver creato il repository `eventour`, puoi caricare un file N-Triples via HTTP:

```bash
./scripts/upload-nt.sh ./import/file.nt
```

Equivalente con `curl`:

```bash
curl \
  -X POST \
  -H "Content-Type: application/n-triples" \
  --data-binary "@./import/file.nt" \
  http://localhost:7200/repositories/eventour/statements
```

L'endpoint di update/import del repository e lo stesso endpoint RDF4J con `/statements`.

## Variabili utili per gli script

Gli script usano questi default:

```bash
GRAPHDB_URL=http://localhost:7200
REPO_ID=eventour
```

Puoi sovrascriverli cosi:

```bash
REPO_ID=altro_repo ./scripts/query.sh queries/example.rq
GRAPHDB_URL=http://localhost:7201 ./scripts/query.sh queries/example.rq
```
