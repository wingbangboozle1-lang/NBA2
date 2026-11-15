"""v3: two independent estimators, disagreement as the confidence signal.

This package is deliberately import-light: it re-exports nothing, so that importing one module
(for example ``official``, which holds only transcribed constants) never drags in the model,
the backtest and the page renderer.
"""
