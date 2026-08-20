# Univariate Transformer

The univariate Transformer is the first forecasting phase in PREDAP. It builds
a baseline forecast from the target history and temporal features before the
residual correction phases run.

## Responsibilities

- Build the base Transformer architecture.
- Train one model per target code, lookback and forecast horizon.
- Evaluate the baseline forecast.
- Produce residuals for diagnostic and seasonal correction.

## Architectures

The codebase includes several Transformer-style architecture files:

- base Transformer;
- Informer-inspired variant;
- LogSparse Transformer variant;
- LSTNet-style variant.

## Relevant Source Areas

- `src/model_architechture/model_architecture_univ_transformer.py`
- `src/model_architechture/transformer_univ_architechtures/`
- `src/training/training_univ_transformer.py`

