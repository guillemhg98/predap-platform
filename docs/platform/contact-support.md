# Contact and Support

Use this page to choose the right support channel without exposing private data.

## Public Support

Open a GitHub issue when the question can be discussed publicly and reproduced
with synthetic data or sanitized logs.

| Area | Repository |
|---|---|
| Platform docs, GitHub Pages, orchestration | [predap-platform](https://github.com/guillemhg98/predap-platform/issues) |
| Retrieval outputs and schema contracts | [predap-data-retrieval](https://github.com/guillemhg98/predap-data-retrieval/issues) |
| CCLR feature selection | [predap-cclr](https://github.com/guillemhg98/predap-cclr/issues) |
| Training, quantization and MLflow | [predap-training](https://github.com/guillemhg98/predap-training/issues) |
| Model bundle validation and inference | [predap-inference](https://github.com/guillemhg98/predap-inference/issues) |

## What to Include

A useful public issue includes:

- the repository and page or command involved;
- the exact command you ran;
- operating system and shell;
- Python and Docker versions when relevant;
- sanitized logs;
- whether the problem happens with toy data, real data or both.

## Sensitive Reports

Do not post private healthcare data, credentials, connection strings, MLflow
artifacts, screenshots of real records, model weights trained on real data or
production predictions in public issues.

For security, privacy or accidental data exposure, use a private maintainer
channel and follow the repository `SECURITY.md` policy. If a credential may have
been exposed, rotate or revoke it before opening a public fix.

## Private Deployment Questions

Questions about institutional connectors, private data retrieval, real CCLR
outputs or operational schedules usually belong in the private deployment
channel for the organization running PREDAP. The public repositories document
the contracts and commands, but they intentionally do not contain private
credentials, raw extracts or deployment-specific access details.
