# License and Permitted Use

PREDAP public repositories are distributed under the Apache License 2.0 unless a
specific repository says otherwise.

This page is an operational summary. The binding license text is the `LICENSE`
file in each repository.

## What the License Allows

Apache 2.0 generally allows you to:

- use the code;
- copy and distribute the code;
- modify the code;
- distribute modified versions;
- use the code in private or commercial settings;
- receive the patent license described in the Apache 2.0 terms.

When distributing copies or modified versions, keep the license notice and
clearly mark files you changed.

## Warranty and Liability

The software is provided without warranties. You are responsible for deciding
whether PREDAP is appropriate for your environment, data, governance process and
operational risk.

## Intended Use

PREDAP is intended as forecasting and engineering infrastructure for demand
planning workflows. It can help teams build reproducible pipelines around:

- historical demand and diagnosis time series;
- CCLR feature selection;
- Transformer training and quantization;
- MLflow tracking;
- batch prediction exports.

## Use Boundaries

The public repositories are not a clinical decision system, not a medical
device, and not a substitute for local validation, monitoring, institutional
approval or human review.

Before using real predictions operationally, validate:

- source-data quality and coverage;
- target-code definitions;
- forecast horizons and lookback windows;
- model performance by subgroup and time period where appropriate;
- drift, retraining and rollback procedures;
- privacy, security and access controls.

## Data and Model Artifacts

The public license covers the public source code and documentation. It does not
grant rights to private healthcare datasets, institutional extracts, production
predictions, MLflow runs, trained model weights or other artifacts that are not
published in the repositories.

Those private assets remain governed by the organization that owns or processes
them.

## Third-Party Dependencies

PREDAP uses third-party libraries and Docker images. Their own licenses and
terms continue to apply. Review dependency licenses before redistribution or
production deployment.

## Publication Rule

Only publish code, documentation, CI configuration and synthetic examples. Keep
real data, credentials, runtime outputs, MLflow artifacts and trained weights
outside GitHub.

Run the safety check before every public export:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_github_safety.ps1 `
  -Path dist\github-repos
```
