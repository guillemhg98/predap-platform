# Submodules

The platform repository can pin exact versions of each PREDAP module through
Git submodules.

## Add Submodules

```powershell
mkdir modules
git submodule add https://github.com/<org>/predap-data-retrieval.git modules/predap-data-retrieval
git submodule add https://github.com/<org>/predap-cclr.git modules/predap-cclr
git submodule add https://github.com/<org>/predap-training.git modules/predap-training
git submodule add https://github.com/<org>/predap-inference.git modules/predap-inference
git commit -m "Add PREDAP module submodules"
```

## Clone With Submodules

```bash
git clone --recurse-submodules https://github.com/<org>/predap-platform.git
```

## Update Submodules

```bash
git submodule update --remote --merge
git add modules .gitmodules
git commit -m "Update PREDAP submodules"
```

## Work Inside a Submodule

```bash
cd modules/predap-inference
git checkout main
git pull
```

Commit and push inside the submodule first, then commit the updated submodule
pointer in `predap-platform`.

