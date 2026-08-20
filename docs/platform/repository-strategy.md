# Repository Strategy

PREDAP should be published as a small ecosystem of independent repositories.
Each repository has one owner boundary and exchanges artifacts with the others
through documented contracts.

## Target Repositories

| Repository | Local source | Publish |
|---|---|---|
| `predap-platform` | Root files, `docker-compose.yml`, docs, workflows | Orchestration and docs. |
| `predap-data-retrieval` | `AQUAS_DATA_RETRIEVAL-git/` | Data connector code and schema validators. |
| `predap-cclr` | `CCLR_PREDAP/` | CCLR algorithms and docs. |
| `predap-training` | `src/`, `conf/`, `main_train*.py`, selected `scripts/` | Training and quantization. |
| `predap-inference` | `PREDAP_INFERENCE/` | Model validation and prediction pipelines. |

## Do Not Publish

- `runtime/`
- `mlruns/`
- `outputs/`
- `plots/`
- `AQUAS_DATA_RETRIEVAL-git/data/`
- `CCLR_PREDAP/data/`
- real model weights
- real prediction outputs
- `.env`

Every exported repository also includes `DATA_POLICY.md`, `SECURITY.md`,
`CONTRIBUTING.md`, `LICENSE`, `.gitattributes` and
`scripts/check_github_safety.ps1`.

## Export Workflow

The export workflow must run from the complete source workspace, not from an
already exported `predap-platform` clone. The complete workspace contains the
root platform files plus `AQUAS_DATA_RETRIEVAL-git/`, `CCLR_PREDAP/`,
`PREDAP_INFERENCE/`, `src/`, `conf/` and training scripts.

Before exporting, run the public smoke workflow and docs build:

```powershell
python examples\synthetic\predap_synthetic_workflow.py --output-dir runtime\synthetic_demo
python PREDAP_INFERENCE\production\validate_model_bundle.py --model-folder runtime\synthetic_demo\model_bundle
.\.venv-docs\Scripts\python.exe -m mkdocs build --strict --site-dir runtime\docs_check
```

Stage clean copies:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_independent_repos.ps1 -OutputRoot dist\github-repos -Force -RunSafetyCheck
```

Preview local Git initialization and remote configuration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 -ReposRoot dist\github-repos -RemoteBaseUrl https://github.com/<org> -DryRun
```

Push only after confirming the final GitHub organization and repository names:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_independent_repos.ps1 -ReposRoot dist\github-repos -RemoteBaseUrl https://github.com/<org> -Push
```

The GitHub repositories must already exist before the push. Create empty
repositories in GitHub with these names, or use GitHub CLI:

```powershell
$Org = "<org>"
$Repos = @(
  "predap-platform",
  "predap-data-retrieval",
  "predap-cclr",
  "predap-training",
  "predap-inference"
)

foreach ($Repo in $Repos) {
  gh repo create "$Org/$Repo" --private
}
```

## Submodule Layout

The platform repo can consume the independent repos as Git submodules:

```text
modules/
  predap-data-retrieval/
  predap-cclr/
  predap-training/
  predap-inference/
```

Suggested commands after the GitHub repositories exist:

```powershell
git submodule add https://github.com/<org>/predap-data-retrieval.git modules/predap-data-retrieval
git submodule add https://github.com/<org>/predap-cclr.git modules/predap-cclr
git submodule add https://github.com/<org>/predap-training.git modules/predap-training
git submodule add https://github.com/<org>/predap-inference.git modules/predap-inference
```
