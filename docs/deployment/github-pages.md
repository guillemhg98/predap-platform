# GitHub Pages

PREDAP documentation is built with MkDocs Material.

## Platform Pages

The `predap-platform` repository is the canonical documentation site for the
whole ecosystem.

Local build:

```powershell
pip install -r docs-requirements.txt
mkdocs build --strict
```

GitHub setup:

1. Open `predap-platform` on GitHub.
2. Go to **Settings > Pages**.
3. Set **Source** to **GitHub Actions**.
4. Push to `main`.
5. Wait for the `Docs` workflow to finish.

## Submodule Pages

The exported repositories are also prepared for their own Pages sites when they
include `mkdocs.yml` and `.github/workflows/docs.yml`:

| Repository | Pages status |
|---|---|
| `predap-platform` | Full ecosystem docs. |
| `predap-data-retrieval` | Data contract docs. |
| `predap-cclr` | CCLR module docs. |
| `predap-training` | Training workflow docs. |
| `predap-inference` | Model bundle and prediction contract docs. |

For each repository:

```powershell
git push -u origin main
```

Then enable **Settings > Pages > GitHub Actions**.

## Safety

GitHub Pages workflows publish only generated documentation. They do not upload
`runtime/`, `mlruns/`, real datasets or private model files because those paths
are ignored and excluded from the export.

Before publishing exported repos:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_github_safety.ps1 -Path dist\github-repos
```

