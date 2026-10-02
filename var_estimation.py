#This practical assignment aims to estimate the Value at Risk (VaR) of a portfolio
#consisting of stocks and using the NASDAQ index as a market benchmark
#For the code to run smoothly, ensure that your data file contains solely the name of your two stocks and 
#that your market benchmark's column name is hardcoded as such:
#
#{index}_INDEX

# ------------------------------------------------------------
# USER PARAMETERS — update these before running
# ------------------------------------------------------------

weights = [0.25, 0.75]          # portfolio weights, must sum to 1
betas = {"GameStop": -0.21, "NVIDIA": 1.75}  # keys must match the Excel column names, in the same order
parameter_lambda = 0.94
alpha = 0.01
risk_horizon = 1
trading_days = 250
stress_year = 2021              # update to change the stress period

#-------------------------------------------------------------
# PART 0 - Fetching the data
#-------------------------------------------------------------

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import norm

folder = Path(__file__).parent / "input"
files = list(folder.glob("*.xlsx")) #make sure to store your data as a .xlsx file, currently this code supports only one file at a time

dataframes = {}
if not files:
    raise SystemExit(f"No .xlsx files in directory {folder}")
else:
    for file in files:
        dataframes[file.stem] = pd.read_excel(file)
        print(f"Reading: {file.name}")

df = list(dataframes.values())[0].copy()

#-------------------------------------------------------------
# PART 1 - Lognormal Returns
#-------------------------------------------------------------

#Calculating returns
columns = list(df.columns)

for column in columns:
    if column != columns[0] and not column.endswith("_INDEX"):
        df[f"{column}_LogReturns"] = np.log(df[column] / df[column].shift(1))

columns = list(df.columns)

# Calculating Portfolio
log_return_cols = [col for col in columns if col.endswith("_LogReturns") and "_INDEX" not in col]
df["Portfolio_LogReturns"] = sum(df[col] * weight for col, weight in zip(log_return_cols, weights))
columns = list(df.columns)

df_raw = df.copy()
df = df.iloc[1:]

# PLOTTING
plots = Path(__file__).parent / "plots"

# Stock Price Evolution
price_columns = [col for col in columns if not col.endswith("_LogReturns") and not col.endswith("_INDEX") and col != columns[0]]
title = "Stock Prices of " + ", ".join(price_columns)

fig, ax = plt.subplots()
for column in price_columns:
    ax.plot(df[columns[0]], df[column], label=column)
ax.set_title(title)
ax.legend()
fig.savefig(plots / "Stock Prices.png")
plt.close(fig)

# Histograms
for column in columns:
    if column.endswith("_LogReturns"):
        fig, ax = plt.subplots()
        ax.hist(df[column].dropna(), bins=50)
        ax.set_title(f"Log Returns Histogram of {column.replace('_LogReturns', '')}")
        fig.savefig(plots / f"{column}.png")
        plt.close(fig)

# All Returns line chart
fig, ax = plt.subplots(figsize=(14, 6))
for column in log_return_cols:
    label = column.replace("_LogReturns", "")
    ax.plot(df[columns[0]], df[column], label=label, linewidth=0.8)
ax.plot(df[columns[0]], df["Portfolio_LogReturns"], label="Global Portfolio", color="black", linewidth=0.8)
ax.set_title("Log Returns for Stocks and Global Portfolio")
ax.set_xlabel("Date")
ax.set_ylabel("Log Returns")
ax.legend(loc="center right")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.4%}"))
fig.savefig(plots / "Log Returns for Stocks and Global Portfolio.png")
plt.close(fig)

#-------------------------------------------------------------
# PART 2 - Calculating Vols and Correlations
#-------------------------------------------------------------

df2 = df_raw.copy().drop(columns=[col for col in df_raw.columns if col.endswith("_INDEX")]).reset_index(drop=True)

#Returns ^ 2

for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        df2[f"{base}_Returns^2"] = df2[column] ** 2

columns = list(df2.columns)

#Volatility

for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        df2[f"{base}_Volatility"] = np.sqrt(df2[f"{base}_Returns^2"].expanding().mean())

columns = list(df2.columns)

#Adj Variance
for column in columns:
    if column.endswith("_Returns^2"):
        base = column.replace("_Returns^2", "")
        
        adj_var = [None] * len(df2)
        adj_var[0] = df2[column].mean()
        adj_var[1] = (1 - parameter_lambda) * df2[column].iloc[1] + parameter_lambda * adj_var[0]
        
        for i in range(2, len(df2)):
            adj_var[i] = (1 - parameter_lambda) * df2[column].iloc[i-1] + parameter_lambda * adj_var[i-1]
        df2[f"{base}_AdjVariance"] = adj_var

columns = list(df2.columns)

#Adj Volatility
for column in columns:
    if column.endswith("_AdjVariance"):
        base = column.replace("_AdjVariance", "")
        df2[f"{base}_AdjVolatility"] = np.sqrt(df2[f"{base}_AdjVariance"])

columns = list(df2.columns)

#Covariance and Correlation estimates

return_products_col = [col for col in columns if col.endswith("_LogReturns") and not col.startswith("Portfolio")]
df2["Returns_Products"] = df2[return_products_col].prod(axis=1)
df2.loc[df2.index[0], "Returns_Products"] = np.nan

covar = [None] * len(df2)
covar[0] = df2["Returns_Products"].mean()
covar[1] = (1 - parameter_lambda) * df2["Returns_Products"].iloc[1] + parameter_lambda * covar[0]

for i in range(2, len(df2)):
    covar[i] = (1 - parameter_lambda) * df2["Returns_Products"].iloc[i-1] + parameter_lambda * covar[i-1]
df2["Covariance"] = covar

correlation_col = [col for col in columns if col.endswith("_AdjVariance") and not col.startswith("Portfolio")]
df2["Correlation"] = df2["Covariance"] / np.sqrt(df2[correlation_col[0]] * df2[correlation_col[1]])

#Adjusted Returns

for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        last_adj_vol = df2[f"{base}_AdjVolatility"].iloc[-1]
        df2[f"{base}_AdjReturns"] = df2[f"{base}_LogReturns"] * (last_adj_vol / df2[f"{base}_AdjVolatility"])

columns = list(df2.columns)

#Annual Volatility
vols = {}
for column in columns:
    if column.endswith("_LogReturns") and not column.startswith("Portfolio"):
        base = column.replace("_LogReturns", "")
        vols[base] = np.sqrt(trading_days/risk_horizon) * df2[f"{base}_AdjVolatility"].iloc[-1]
        print(f"{base}'s annual volatility is {vols[base]} ")

df2_vols = pd.DataFrame(vols.items(), columns=["Stock", "Annual Volatility"])
print(df2_vols)

#Annual Correlation
corr = df2["Correlation"].iloc[-1]
print(f"The annual correlation of the portfolio is {corr}")

#Annual Covariance matrix
stock_names = list(vols.keys())
vol_array = np.array(list(vols.values()))
vol_matrix = np.outer(vol_array, vol_array)
corr_matrix = np.array([[1, corr], [corr, 1]])
cov_matrix = vol_matrix * corr_matrix

print("Annual Covariance Matrix:")
print(pd.DataFrame(cov_matrix, index=stock_names, columns=stock_names))

# PLOTTING

# EWMA Volatilities
adj_vol_cols = [col for col in columns if col.endswith("_AdjVolatility")]

fig, ax = plt.subplots(figsize=(14, 6))
for col in adj_vol_cols:
    label = col.replace("_AdjVolatility", "") + " Vol"
    color = "black" if col.startswith("Portfolio") else None
    ax.plot(df2[columns[0]], df2[col], label=label, linewidth=0.8, color=color)

ax.set_title("EWMA Volatilities")
ax.set_xlabel("Date")
ax.set_ylabel("Volatility")
ax.legend(loc="center right")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.4%}"))
fig.savefig(plots / "EWMA Volatilities.png")
plt.close(fig)

# EWMA Covariances
stock_names_str = " and ".join(stock_names)

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(df2[columns[0]], df2["Covariance"], label="Covariances", linewidth=0.8, color="cyan")
ax.set_title(f"EWMA Covariances between {stock_names_str}")
ax.set_xlabel("Date")
ax.set_ylabel("Covariance")
ax.legend(loc="center right")
fig.savefig(plots / "EWMA Covariances.png")
plt.close(fig)

#-------------------------------------------------------------
# PART 3 - VaR estimation
#-------------------------------------------------------------

index_cols = [col for col in df_raw.columns if col.endswith("_INDEX")]
keep = [col for col in df2.columns if not any(col.endswith(suffix) for suffix in ["_LogReturns","_Returns^2", "_Volatility", "Returns_Products", "Covariance", "Correlation"])]
df3 = pd.concat([df2[keep], df_raw[index_cols]], axis=1).reset_index(drop=True)
columns = list(df3.columns)

#Calculating Returns, Returns^2, Volatility, AdjVariance, AdjVolatility, AdjReturns for the INDEX

#Calculating returns
for column in columns:
    if column != columns[0] and column.endswith("_INDEX"):
        df3[f"{column}_LogReturns"] = np.log(df3[column] / df3[column].shift(1))

columns = list(df3.columns)

#Returns ^ 2
for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        df3[f"{base}_Returns^2"] = df3[column] ** 2

columns = list(df3.columns)

#Volatility
for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        df3[f"{base}_Volatility"] = np.sqrt(df3[f"{base}_Returns^2"].expanding().mean())

columns = list(df3.columns)

#Adj Variance
for column in columns:
    if column.endswith("_Returns^2"):
        base = column.replace("_Returns^2", "")
        
        adj_var = [None] * len(df3)
        adj_var[0] = df3[column].mean()
        adj_var[1] = (1 - parameter_lambda) * df3[column].iloc[1] + parameter_lambda * adj_var[0]
        
        for i in range(2, len(df3)):
            adj_var[i] = (1 - parameter_lambda) * df3[column].iloc[i-1] + parameter_lambda * adj_var[i-1]
        df3[f"{base}_AdjVariance"] = adj_var

columns = list(df3.columns)

#Adj Volatility
for column in columns:
    if column.endswith("_AdjVariance"):
        base = column.replace("_AdjVariance", "")
        df3[f"{base}_AdjVolatility"] = np.sqrt(df3[f"{base}_AdjVariance"])

columns = list(df3.columns)

#Adjusted Returns
for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        last_adj_vol = df3[f"{base}_AdjVolatility"].iloc[-1]
        df3[f"{base}_AdjReturns"] = df3[f"{base}_LogReturns"] * (last_adj_vol / df3[f"{base}_AdjVolatility"])
columns = list(df3.columns)

#Covariance and Correlation estimates
index_adj_col = [col for col in columns if col.endswith("_INDEX_AdjReturns")][0]
index_adj_var_col = [col for col in columns if col.endswith("_INDEX_AdjVariance")][0]

df3["Returns_Products_Index_Portfolio"] = df3[index_adj_col] * df3["Portfolio_AdjReturns"]

n = df3["Returns_Products_Index_Portfolio"].iloc[1:].count()
index_port_covar = [None] * len(df3)
index_port_covar[0] = np.dot(df3["Portfolio_AdjReturns"].iloc[1:], df3[index_adj_col].iloc[1:]) * (1 / n)
index_port_covar[1] = (1 - parameter_lambda) * df3["Returns_Products_Index_Portfolio"].iloc[1] + parameter_lambda * index_port_covar[0]

for i in range(2, len(df3)):
    index_port_covar[i] = (1 - parameter_lambda) * df3["Returns_Products_Index_Portfolio"].iloc[i-1] + parameter_lambda * index_port_covar[i-1]

df3["Covariance_Index_Portfolio"] = index_port_covar

columns = list(df3.columns)

df3["Correlation_Index_Portfolio"] = df3["Covariance_Index_Portfolio"] / np.sqrt(df3["Portfolio_AdjVariance"] * df3[index_adj_var_col])

#-------------------------------------------------------------------------------------------------------------------------------------------------
#We'll now calculate the 1-day VaR and ETL
portfolio_vol = df3["Portfolio_AdjVolatility"].iloc[-1]
portfolio_returns = df3["Portfolio_AdjReturns"].mean()

alpha_norminv = norm.ppf(alpha, 0, 1)
alpha_normdis = norm.pdf(alpha_norminv, 0, 1) # non-cumulative normal distribution

var_total_1day = norm.ppf(1 - alpha, 0, 1) * portfolio_vol
print(f"1-day Total VaR: {var_total_1day:.4%}")

etl_1day = ((1/alpha) * portfolio_vol * alpha_normdis)
print(f"1-day ETL: {etl_1day:.4%}")

#-------------------------------------------------------------------------------------------------------------------------------------------------
#We'll now calculate the 10-day VaR and ETL
risk_horizon10 = 10

portfolio_vol10 = np.sqrt(risk_horizon10) * portfolio_vol
portfolio_returns10 = portfolio_returns * risk_horizon10

var_total_10day = norm.ppf(1 - alpha, 0, 1) * portfolio_vol10
print(f"10-day Total VaR: {var_total_10day:.4%}")

etl_10day = ((1/alpha) * portfolio_vol10 * alpha_normdis)
print(f"10-day ETL: {etl_10day:.4%}")

#-------------------------------------------------------------------------------------------------------------------------------------------------
#We'll now calculate the 1-day parametric systemic VaR for the stocks in our portfolio
weighted_betas = {stock: beta * weight for (stock, beta), weight in zip(betas.items(), weights)}
weighted_betas_array = np.array(list(weighted_betas.values()))
portfolio_variance = weighted_betas_array.T @ cov_matrix @ weighted_betas_array
print(f"Portfolio Annual Variance: {portfolio_variance:.6f}")

var_par_1day_portfolio = norm.ppf(1-alpha, 0, 1) * np.sqrt(portfolio_variance * risk_horizon / trading_days)
print(f"1-day Parametric VaR of our Portfolio: {var_par_1day_portfolio:.4%}")

#-------------------------------------------------------------------------------------------------------------------------------------------------
#We'll also calculate the 1-day parametric systemic VaR between our portfolio and the index

index_name = [col for col in df_raw.columns if col.endswith("_INDEX")][0]
market_betas = {"Portfolio": weighted_betas_array.sum(), index_name: 1}

portfolio_annualvol = np.sqrt(trading_days/risk_horizon) * df3["Portfolio_AdjVolatility"].iloc[-1]
index_adj_vol_col = [col for col in columns if col.endswith("_INDEX_AdjVolatility")][0]
index_annualvol = np.sqrt(trading_days/risk_horizon) * df3[index_adj_vol_col].iloc[-1]
annual_corr = df3["Correlation_Index_Portfolio"].iloc[-1]

sys_vols = np.array([portfolio_annualvol, index_annualvol])
sys_vol_matrix = np.outer(sys_vols, sys_vols)
sys_corr_matrix = np.array([[1, annual_corr], [annual_corr, 1]])
sys_cov_matrix = sys_vol_matrix * sys_corr_matrix

print(f"Systemic Covariance Matrix (Portfolio and {index_name}):")
print(pd.DataFrame(sys_cov_matrix, index=["Portfolio", index_name], columns=["Portfolio", index_name]))

market_betas_array = np.array(list(market_betas.values()))
market_variance = market_betas_array.T @ sys_cov_matrix @ market_betas_array
print(f"Annual Variance: {market_variance:.6%}")

var_sys_1day = norm.ppf(1-alpha, 0, 1) * np.sqrt(market_variance * risk_horizon / trading_days)
print(f"1-day Parametric VaR: {var_sys_1day:.4%}")

#-------------------------------------------------------------
# PART 4 - Cornish-Fisher VaR estimation
#-------------------------------------------------------------
df4 = df_raw.copy().drop(columns=[col for col in df_raw.columns if col.endswith("_INDEX")]).reset_index(drop=True)
columns = list(df4.columns)

for column in columns: #The idea is that more recent observations are more relevant for risk estimation than older ones.
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        n = df4[f"{base}_LogReturns"].count()
        ewma_weights = [(1 - parameter_lambda) * (parameter_lambda ** i) for i in range(n)]
        ewma_weights = ewma_weights[::-1]  # reverse so most recent = 1-lambda
        df4[f"{base}_Weight"] = [np.nan] + ewma_weights
columns = list(df4.columns)

for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        sorted_values = [np.nan] + df4[f"{base}_LogReturns"].sort_values().dropna().tolist()
        df4[f"{base}_OrderedReturns"] = sorted_values
columns = list(df4.columns)

for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        sorted_index = df4[f"{base}_LogReturns"].sort_values().index
        ordered_weights = [np.nan] + df4[f"{base}_Weight"].loc[sorted_index].dropna().tolist()
        df4[f"{base}_Ordered_wi"] = ordered_weights

columns = list(df4.columns)

for column in columns:
    if column.endswith("_Weight"):
        base = column.replace("_Weight", "")
        cum_prob = [np.nan] * len(df4)
        cum_prob[1] = df4[f"{base}_Ordered_wi"].iloc[1]
        
        for i in range(2, len(df4)):
            cum_prob[i] = df4[f"{base}_Ordered_wi"].iloc[i] + cum_prob[i-1]
        
        df4[f"{base}_CumulativeProb"] = cum_prob
columns = list(df4.columns)

#Computing parameters
hist_vols = {}
for column in columns:
    if column.endswith("_LogReturns") and not column.startswith("Portfolio"):
        base = column.replace("_LogReturns", "")
        hist_vols[base] = df4[f"{base}_LogReturns"].std() * np.sqrt(trading_days / risk_horizon)
        print(f"{base} Historical Volatility: {hist_vols[base]:.4%}")

log_return_cols = [col for col in columns if col.endswith("_LogReturns") and not col.startswith("Portfolio")]
hist_corr = df4[log_return_cols[0]].corr(df4[log_return_cols[1]])
print(f"Historical Correlation: {hist_corr:.4f}")

#Historical Covariance matrix
stock_names = list(hist_vols.keys())
hist_vol_array = np.array(list(hist_vols.values()))
hist_vol_matrix = np.outer(hist_vol_array, hist_vol_array)
hist_corr_matrix = np.array([[1, hist_corr], [hist_corr, 1]])
hist_cov_matrix = hist_vol_matrix * hist_corr_matrix

print("Historical Covariance Matrix:")
print(pd.DataFrame(hist_cov_matrix, index=stock_names, columns=stock_names))

#We'll now calculate the Stand-Alone Historical 1-day VaR
for (stock, vol), (s, beta_w) in zip(hist_vols.items(), weighted_betas.items()):
    VaR_standalone = abs(-norm.ppf(1 - alpha, 0, 1) * np.sqrt(risk_horizon / trading_days) * beta_w * vol)
    print(f"{stock} Stand-Alone Historical 1-day VaR: {VaR_standalone:.4%}")

var_hist_1day = -np.percentile(df4["Portfolio_LogReturns"].iloc[1:], alpha * 100)
print(f"1-day Historical VaR: {var_hist_1day:.4%}")

#We'll now calculate the Cornish-Fisher 1-day VaR

#Sample Statistics
annualized_mean = df4["Portfolio_LogReturns"].mean() * trading_days
annualized_vol = df4["Portfolio_LogReturns"].std() * np.sqrt(trading_days)
skewness = df4["Portfolio_LogReturns"].skew()
kurtosis = df4["Portfolio_LogReturns"].kurt()
horizon_annualized_mean = annualized_mean * (risk_horizon/trading_days)
horizon_annualized_vol = annualized_vol * np.sqrt(risk_horizon/trading_days)

#Cornish Fisher Approximation
part1 = -norm.ppf(1-alpha, 0, 1)
part2 = skewness/6 * (part1 ** 2 -1)
part3 = kurtosis/24 * part1 * (part1 ** 2 -3)
part4 = ((skewness ** 2) / 36) * part1 * (2*part1**2 - 5)

cornish = part1 + part2 + part3 - part4

var_cornish_1day = -(cornish * horizon_annualized_vol + horizon_annualized_mean)
print(f"1-day Cornish VaR: {var_cornish_1day:.4%}")

#We'll now calculate the Cornish-Fisher 1-day ETL
alfa = -part1
bravo = norm.pdf(alfa, 0, 1)
charlie = -bravo/alpha
delta = charlie + skewness/6 * (charlie ** 2 -1) + kurtosis/24 * charlie * (charlie ** 2 - 3) - skewness**2 / 36 * charlie * (2*charlie**2 - 5)

etl_cornish1day = -(delta * horizon_annualized_vol - horizon_annualized_mean)
print(f"1-day Cornish-Fisher ETL: {etl_cornish1day:.4%}")

# PLOTTING
cum_prob_cols = [col for col in columns if col.endswith("_CumulativeProb")]

fig, ax = plt.subplots(figsize=(14, 6))
for col in cum_prob_cols:
    label = col.replace("_CumulativeProb", "") + " Cumulative Prob"
    color = "black" if col.startswith("Portfolio") else None
    ax.plot(df4[columns[0]], df4[col], label=label, linewidth=0.8, color=color)

ax.set_title("Cumulatives Distributions for Stocks and Portfolio")
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative Distribution")
ax.legend(loc="center right")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.2%}"))
fig.savefig(plots / "Cumulative Distributions.png")
plt.close(fig)

#-------------------------------------------------------------
# PART 5 - Stressed period and historical VaR
#-------------------------------------------------------------
df5 = df_raw.copy().drop(columns=[col for col in df_raw.columns if col.endswith("_INDEX")]).reset_index(drop=True)
columns = list(df5.columns)

dfstress_period = df5[df5[columns[0]].dt.year == stress_year]

#Sample moments stress_year
stressed_mean = {}
for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        stressed_mean[base] = dfstress_period[f"{base}_LogReturns"].mean()
        print(f"{base} Stressed Mean: {stressed_mean[base]:.4%}")

stressed_std = {}
for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        stressed_std[base] = dfstress_period[f"{base}_LogReturns"].std()
        print(f"{base} Stressed Standard Deviation: {stressed_std[base]:.4%}")

stressed_skewness = {}
for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        stressed_skewness[base] = dfstress_period[f"{base}_LogReturns"].skew()
        print(f"{base} Stressed Skewness: {stressed_skewness[base]:.4f}")

stressed_kurtosis = {}
for column in columns:
    if column.endswith("_LogReturns"):
        base = column.replace("_LogReturns", "")
        stressed_kurtosis[base] = dfstress_period[f"{base}_LogReturns"].kurt()
        print(f"{base} Stressed Kurtosis: {stressed_kurtosis[base]}")

log_return_cols = [col for col in columns if col.endswith("_LogReturns") and not col.startswith("Portfolio")]
stressed_corr = dfstress_period[log_return_cols[0]].dropna().corr(dfstress_period[log_return_cols[1]].dropna())
print(f"Stressed Correlation: {stressed_corr:.4f}")

#Historical Covariance Matrix
hist_cov_matrix = df5[log_return_cols].cov()
print("Historical Covariance Matrix:")
print(hist_cov_matrix)

#Stressed Covariance Matrix
stressed_cov_matrix = dfstress_period[log_return_cols].cov()
print("Stressed Covariance Matrix:")
print(stressed_cov_matrix)

#Historical Cholesky, Q
hist_cholesky = np.linalg.cholesky(hist_cov_matrix.values)
print("Historical Cholesky Q:")
print(pd.DataFrame(hist_cholesky, index=stock_names, columns=stock_names))

#Stressed Cholesky, Q*
stressed_cholesky = np.linalg.cholesky(stressed_cov_matrix.values)
print("Stressed Cholesky Q*:")
print(pd.DataFrame(stressed_cholesky, index=stock_names, columns=stock_names))

#Transformation Matrix
transform_matrix = (stressed_cholesky @ np.linalg.inv(hist_cholesky)).T
print("Transform Matrix:")
print(pd.DataFrame(transform_matrix, index=stock_names, columns=stock_names))

#Calculating Returns*
returns_matrix = df5[log_return_cols].values
transformed = returns_matrix @ transform_matrix
for i, base in enumerate([col.replace("_LogReturns", "") for col in log_return_cols]):
    df5[f"{base}_Returns*"] = transformed[:, i]
columns = list(df5.columns)

return_sharp_cols = [col for col in columns if col.endswith("_Returns*")]
df5["Portfolio_Returns*"] = sum(df5[col] * weight for col, weight in zip(return_sharp_cols, weights))
columns = list(df5.columns)

#Calculating Stressed Portfolio Historical VaR
stressed_var = -np.percentile(df5["Portfolio_Returns*"].iloc[1:], alpha * 100)
print(f"Stressed Portfolio Historical VaR: {stressed_var:.4%}")
