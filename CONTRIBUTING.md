# Contributing

Thanks for improving PREDAP. Keep changes small, documented, and safe to publish.

## Local Checks

Run the lightweight checks before opening a pull request:

```powershell
python examples/synthetic/predap_synthetic_workflow.py --output-dir runtime/synthetic_demo
python -m py_compile examples/synthetic/predap_synthetic_workflow.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\export_independent_repos.ps1 -OutputRoot dist\github-repos -Force -RunSafetyCheck
```

Module repositories may have narrower CI commands in their own `.github`
workflows. Inside an exported repository, run
`scripts/check_github_safety.ps1 -Path .` before pushing.

## Data Safety

Follow [DATA_POLICY.md](DATA_POLICY.md). Real data, derived exports, trained
model weights, runtime outputs, `.env` files, and credentials must stay outside
Git.

## Style

- Prefer existing module patterns over new abstractions.
- Keep synthetic examples deterministic and small.
- Update documentation when changing public contracts.
- Keep public function signatures typed where practical.
