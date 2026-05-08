# Queries

This folder contains competency and application-oriented SPARQL queries.

The detailed competency-query report, including the full SPARQL text and the recorded result for each query, is available in `docs/competency-queries.md`. It can be regenerated with:

```bash
python scripts/16_generate_competency_query_report.py
```

| Query | Purpose | Expected result |
|---|---|---:|
| CQ01 | Count places by Eventour role | 3 rows |
| CQ02 | Retrieve entities in NIL 1 | 3,097 rows |
| CQ03 | Primary POIs near transport | 200 rows, limit reached |
| CQ04 | Services near primary POIs | 300 rows, limit reached |
| CQ05 | Event-area candidates | 100 rows, limit reached |
| CQ06 | NIL infrastructure profile | 50 rows, limit reached |
| CQ07 | Underserved primary POIs | 100 rows, limit reached |
| CQ08 | Multimodal accessibility profile | 100 rows, limit reached |
| CQ09 | Provenance audit | 1 row |
| CQ10 | Operational support score | 100 rows, limit reached |
