# Public Data Policy

PREDAP public repositories are code and documentation repositories. They must
not contain real healthcare data, institutional extracts, production model
artifacts, or credentials.

## Allowed

- Source code.
- Documentation.
- CI workflows.
- Configuration templates with fake or local-only values.
- Small synthetic fixtures under `examples/synthetic/`.
- Dummy model bundles created only for smoke tests and tutorials.

## Not Allowed

- Real clinical, administrative, or institutional datasets.
- Aggregated exports derived from real healthcare systems.
- CSV, Excel, Parquet, database, RDS, or archive files from real systems.
- Model weights or serialized models trained on real data.
- MLflow runs, runtime folders, plots, logs, or production predictions.
- `.env` files, tokens, passwords, private keys, or connection strings.

## Working With Private Data

Keep private data and artifacts outside Git. Use local ignored folders such as
`runtime/` or `private_runtime/`, secure object storage, or a private artifact
registry. Only publish synthetic examples that can be regenerated from public
code.

