# Portfolio Value at Risk (VaR) Estimation

A Python implementation of a multi-method Value at Risk framework for a two-asset portfolio, replicating and extending an Excel-based risk model.

## Overview

This project estimates the Value at Risk (VaR) and Expected Tail Loss (ETL) of a portfolio consisting of two stocks (GameStop and NVIDIA) using five distinct methodologies. It reads price data from an Excel file, performs all calculations programmatically, and exports charts to a plots folder.

## Project Structure

```
input/          # Place your .xlsx price data file here
plots/          # Generated charts are saved here
var_estimation.py  # Main script
```

## Methodologies

- **Parametric VaR** — based on EWMA volatility and normal distribution (1-day and 10-day)
- **Parametric Systemic VaR** — incorporates stock betas and a market index (NASDAQ)
- **Historical VaR** — empirical percentile of portfolio log returns
- **Cornish-Fisher VaR** — adjusts for skewness and excess kurtosis
- **Stressed Historical VaR** — applies a stress transformation matrix derived from a user-defined stress period

## Key Parameters

At the top of the script, update the following before running:

| Parameter | Description |
|---|---|
| `weights` | Portfolio weights per stock (must sum to 1) |
| `betas` | Market betas per stock |
| `parameter_lambda` | EWMA decay factor (default: 0.94) |
| `alpha` | Significance level (default: 0.01) |
| `risk_horizon` | Risk horizon in days (default: 1) |
| `trading_days` | Trading days per year (default: 250) |
| `stress_year` | Year used as the stress period (default: 2021) |

## Input Data Format

The Excel file should contain:
- A `Date` column as the first column
- One column per stock (e.g. `GameStop`, `NVIDIA`)
- A market index column suffixed with `_INDEX` (e.g. `NASDAQ_INDEX`)

## Output

**Printed results:**
- Annual volatilities and correlations
- Covariance matrices (EWMA, Historical, Stressed)
- Cholesky and Transform matrices
- VaR and ETL estimates across all methods

**Charts saved to `/plots`:**
- Stock price evolution
- Log return histograms per asset
- Log returns time series (stocks + portfolio)
- EWMA volatilities over time
- EWMA covariances over time
- Cumulative return distributions

## Dependencies

```
pandas
numpy
matplotlib
scipy
openpyxl

```

Install with:
```
pip install pandas numpy matplotlib scipy openpyxl
```

## Notes

- For portfolios with more than 2 stocks, update the `weights` list and `betas` dictionary accordingly
- The stress period is dynamic — change `stress_year` to any year present in the data
- Hardcoded file paths use Windows format — update the `folder` and `plots` variables to match your directory structure
