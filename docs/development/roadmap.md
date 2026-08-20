# Roadmap

## Current Platformization Work

- [x] Public data policy: code, docs and synthetic examples only.
- [x] Synthetic end-to-end workflow for retrieval, dummy training and dummy inference.
- [x] Model bundle validator for externally uploaded models.
- [x] Repository split strategy for data retrieval, CCLR, training and inference.
- [x] GitHub Pages workflow.
- [x] GitHub safety check for accidental data/model publication.
- [x] Export production quantized-model manifest metadata from training.

## Short Term

- [x] Create final GitHub repositories under the selected organization.
- [x] Push `predap-platform`, `predap-data-retrieval`, `predap-cclr`,
      `predap-training` and `predap-inference`.
- [ ] Add submodules back into the platform repository after remotes exist.
- [ ] Add pytest tests around the synthetic contract validators.
- [ ] Add release notes for each repository.
- [ ] Add private-runtime contract checks to the private release checklist.
- [ ] Add automated tests for WAPE-based stage-aware inference selection.

## Medium Term

- [ ] Add a real data connector interface with private adapters excluded from
      public GitHub.
- [ ] Add inference input assembly for late-arriving source data and previous
      prediction fallback.
- [ ] Add model registry integration for private deployments.
- [ ] Add CI jobs with optional dependency caches for heavier module imports
      without requiring real data.
- [ ] Add a private smoke fixture that runs a tiny real TensorFlow inference
      path end to end.

## Long Term

- [ ] Online or continual learning with incremental updates.
- [ ] Distributed multi-GPU training.
- [ ] Monitoring dashboards for data freshness, prediction drift and model
      performance.
- [ ] Conformal prediction intervals.
- [ ] Optional orchestration with Airflow, Prefect or a similar scheduler.
