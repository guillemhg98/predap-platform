# Utilities

Utility code supports experiment logging, configuration, memory cleanup,
metrics, plotting and artifact loading.

## Relevant Source Areas

- `src/utils/`
- `src/evaluation/`
- `src/config/`
- `PREDAP_INFERENCE/utils/`

## Important Contracts

Utilities should not hard-code private paths in public examples. Prefer:

- environment variables;
- `.env.example` defaults;
- runtime folders ignored by Git;
- explicit CLI arguments in tutorials.

