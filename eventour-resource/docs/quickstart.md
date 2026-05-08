# Quick Start

```bash
conda env create -f environment.yml
conda activate eventour-resource
make validate
make competency
```

The full KG dump is distributed through Zenodo/GitHub Releases. A small N-Triples sample is available in `data/sample/eventour-milan-sample.nt`.

To rebuild the municipal layer from public sources, first populate the local
source-snapshot directory:

```bash
make download-sources
make prepare-sources
```

To load the full graph into a triplestore, load both the data graph and the patched ontology, or use the release file described in `data/final/DOWNLOAD_FROM_ZENODO.txt`.
