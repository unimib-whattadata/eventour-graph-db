# Source Catalog

The municipal source catalog is stored in `data/source-snapshots/source-snapshots.csv`. It records dataset identifiers, source files, exact feature counts, version evidence, transformation date, and source URL placeholders.

The `source_url` column contains the corresponding Comune di Milano Open Data
landing page for each of the 21 municipal datasets. Raw source snapshots are not
stored in Git. To rebuild the municipal backbone, run:

```bash
python scripts/00_download_sources.py --download
python scripts/01_prepare_municipal_sources.py
```

License references are stored in `data/source-snapshots/source-licenses.csv`.
