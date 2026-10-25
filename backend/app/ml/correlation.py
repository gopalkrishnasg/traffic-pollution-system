from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from app.ml.preprocessing import CANDIDATE_FEATURES


def interpret_correlation(var_name: str, r_val: float | None) -> str:
    if r_val is None or np.isnan(r_val):
        return f"Insufficient variation or sample size to compute correlation for {var_name}."

    abs_r = abs(r_val)
    direction = "positive" if r_val > 0 else "negative"
    if abs_r >= 0.7:
        strength = "Strong"
    elif abs_r >= 0.4:
        strength = "Moderate"
    elif abs_r >= 0.2:
        strength = "Weak"
    else:
        strength = "Negligible"

    return (
        f"{strength} {direction} linear association (r = {r_val:.2f}) between {var_name} and AQI "
        f"in this dataset. Note: Statistical correlation does not prove direct physical causation."
    )


def compute_correlations(df: pd.DataFrame, is_synthetic: bool, dataset_name: str) -> Dict[str, Any]:
    warnings: List[str] = []
    if is_synthetic:
        warnings.append(
            "SYNTHETIC DATASET ACTIVE: Correlation coefficients reflect programmed demonstration "
            "relationships (seed=42) and must not be cited as empirical scientific findings."
        )

    if "aqi" not in df.columns:
        raise ValueError("Target variable 'aqi' is missing from the active dataset.")

    available_vars = [c for c in CANDIDATE_FEATURES if c in df.columns]
    correlations = []

    for var in available_vars:
        total_len = len(df)
        sub = df[[var, "aqi"]].dropna()
        sample_count = len(sub)
        missing_count = total_len - sample_count

        if sample_count < 10:
            warnings.append(f"Variable '{var}' has fewer than 10 valid paired observations.")
            correlations.append(
                {
                    "variable": var,
                    "pearson_r": None,
                    "spearman_rho": None,
                    "sample_count": sample_count,
                    "missing_count": missing_count,
                    "interpretation": f"Too few valid samples ({sample_count}) for reliable statistics.",
                }
            )
            continue

        if sub[var].std() < 1e-8 or sub["aqi"].std() < 1e-8:
            warnings.append(f"Variable '{var}' has near-zero variance.")
            correlations.append(
                {
                    "variable": var,
                    "pearson_r": None,
                    "spearman_rho": None,
                    "sample_count": sample_count,
                    "missing_count": missing_count,
                    "interpretation": f"Variable '{var}' is constant; correlation is undefined.",
                }
            )
            continue

        p_r, _ = pearsonr(sub[var], sub["aqi"])
        s_rho, _ = spearmanr(sub[var], sub["aqi"])

        p_r_clean = round(float(p_r), 4)
        s_rho_clean = round(float(s_rho), 4)

        correlations.append(
            {
                "variable": var,
                "pearson_r": p_r_clean,
                "spearman_rho": s_rho_clean,
                "sample_count": sample_count,
                "missing_count": missing_count,
                "interpretation": interpret_correlation(var, p_r_clean),
            }
        )

    matrix_vars = [v for v in available_vars if df[v].notna().sum() >= 10] + ["aqi"]
    corr_df = df[matrix_vars].corr(method="pearson").round(3)
    pearson_matrix: List[List[float | None]] = []
    for row_var in matrix_vars:
        row_vals = []
        for col_var in matrix_vars:
            val = corr_df.loc[row_var, col_var]
            row_vals.append(None if pd.isna(val) else float(val))
        pearson_matrix.append(row_vals)

    scatter_cols = [c for c in ["aqi"] + available_vars if c in df.columns]
    scatter_df = df[scatter_cols].dropna(subset=["aqi"])
    if len(scatter_df) > 250:
        scatter_df = scatter_df.sample(n=250, random_state=42)

    scatter_samples = []
    for _, row in scatter_df.iterrows():
        item = {}
        for col in scatter_cols:
            val = row[col]
            item[col] = None if pd.isna(val) else round(float(val), 2)
        scatter_samples.append(item)

    return {
        "dataset_name": dataset_name,
        "is_synthetic": is_synthetic,
        "total_rows": len(df),
        "target_variable": "aqi",
        "correlations": correlations,
        "matrix_variables": matrix_vars,
        "pearson_matrix": pearson_matrix,
        "scatter_samples": scatter_samples,
        "warnings": warnings,
    }
