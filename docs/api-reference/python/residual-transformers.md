# Residual Transformers

Residual Transformers implement the second and third correction phases of the
PREDAP training pipeline.

## Phase 2: Diagnostic Residuals

Inputs:

- base univariate forecast;
- observed target history;
- diagnostic covariates selected by CCLR.

Output:

- corrected forecast after diagnostic residual learning.

## Phase 3: Seasonal Residuals

Inputs:

- diagnostic-corrected forecast;
- residual history;
- calendar and seasonal covariates.

Output:

- final corrected forecast used for evaluation and quantization.

## Relevant Source Areas

- `src/model_architechture/model_architecture_residual_transformer.py`
- `src/training/training_residual_transformer.py`
- `src/data_utils/residual_data_preparation.py`

