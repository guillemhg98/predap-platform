# Security Policy

## Supported Use

These repositories are intended for public source code, documentation, CI, and
synthetic examples. Do not open issues, pull requests, or commits that include
real healthcare data, credentials, production predictions, MLflow artifacts, or
model weights trained on real data.

## Reporting a Vulnerability

Report suspected security or data-exposure issues privately to the repository
maintainers. If GitHub private vulnerability reporting is enabled for the
repository, use that path. Otherwise use an agreed private maintainer channel.

Include:

- the affected repository and path;
- whether any secret, real data, or model artifact may be exposed;
- minimal reproduction steps when relevant.

Do not post sensitive samples publicly. If a secret or private dataset was
committed, rotate the secret or revoke access before publishing a fix.

For non-sensitive support questions, use `SUPPORT.md`.

## Pre-Publish Checks

Before pushing a public exported repository, run from that exported repo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_github_safety.ps1 -Path .
```
