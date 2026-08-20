# Data Policy

PREDAP public repositories must be safe to publish.

## Allowed in GitHub

- Source code.
- Documentation.
- Configuration templates with fake values.
- Synthetic dummy datasets.
- Synthetic dummy model bundles.
- CI workflows.

## Forbidden in GitHub

- Real clinical or institutional extracts.
- Aggregated real healthcare data.
- Parquet, CSV, Excel or database files generated from real systems.
- Model weights trained on real data.
- MLflow run folders and artifacts.
- Production predictions.
- Secrets, tokens, passwords and `.env` files.

## Recommended Practice

Use `runtime/`, secure object storage or private artifact registries for real
data and model files. Keep only small public examples under
`examples/synthetic/`.

For allowed code use and license terms, see
[License and Permitted Use](license-and-use.md). For support or sensitive
reports, see [Contact and Support](contact-support.md).
