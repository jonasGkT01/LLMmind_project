import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import hypergeom

def infer_alignment_column(df: pd.DataFrame) -> str:
    candidate_columns = [
        "alignment_score",
        "LLM_mind_alignment_score",
        "llm_brain_alignment_score",
        "score",
    ]

    for col in candidate_columns:
        if col in df.columns:
            return col

    numeric_columns = df.select_dtypes(include="number").columns.tolist()

    if len(numeric_columns) == 1:
        return numeric_columns[0]

    raise ValueError(
        f"Could not infer alignment-score column. Available columns are: {list(df.columns)}"
    )

def infer_model_from_observed_path(path: str) -> str:
    """
        Expected observed path:
        results/alignment_score/{dataset}/{similarity_type}_alignment_scores/{model}_brain_{similarity_type}_alignment_score_{number_of_neighbours}NN.parquet
    """
    name = Path(path).name

    match = re.fullmatch(
        r"(.+)_brain_(.+)_alignment_score_(\d+)NN\.parquet",
        name,
    )

    if match is None:
        raise ValueError(f"Cannot infer model from observed path: {path}")

    return match.group(1)


def infer_model_and_relabel_from_relabelled_path(path: str) -> tuple[str, int]:
    """
        Expected relabelled path:
        results/alignment_score/{dataset}/{similarity_type}_alignment_scores/{model}_brain_{similarity_type}_alignment_score_relabel_{relabel}_{number_of_neighbours}NN.parquet
    """
    name = Path(path).name

    match = re.fullmatch(
        r"(.+)_brain_(.+)_alignment_score_(\d+)NN_relabel_(\d+)\.parquet",
        name,
    )

    if match is None:
        raise ValueError(
            f"Cannot infer model and relabel index from relabelled path: {path}"
        )

    model = match.group(1)
    relabel = int(match.group(4))

    return model, relabel

def read_alignment_dataframe(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    alignment_col = infer_alignment_column(df)

    df = df.copy()
    df["alignment_score"] = df[alignment_col]

    return df

def compute_hypergeometric_statistics(
    observed_df: pd.DataFrame,
    number_of_neighbours: int,
) -> dict:
    """
        Computes the exact hypergeometric expected overlap and concept-wise p-values.

        If alignment_score = common_neighbours / k, then common_neighbours = alignment_score * k.

        The population excludes the labelled concept itself, so:
        M = N - 1

        X ~ Hypergeom(M=N-1, n=k, N=k)
    """

    k = number_of_neighbours
    number_of_concepts = len(observed_df)
    population_size = number_of_concepts - 1

    expected_common_neighbours = (k * k) / population_size
    expected_alignment_score = k / population_size

    observed_common_neighbours = observed_df["alignment_score"] * k

    # Numerical protection: alignment scores may be floats like 0.30000000004.
    observed_common_neighbours = (
        observed_common_neighbours.round().astype(int)
    )

    # Upper-tail p-value: P(X >= x).
    # scipy survival function gives P(X > x - 1), i.e. P(X >= x).
    p_values = hypergeom.sf(
        observed_common_neighbours - 1,
        population_size,
        k,
        k,
    )

    return {
        "number_of_concepts": number_of_concepts,
        "hypergeom_population_size": population_size,
        "number_of_neighbours": k,
        "hypergeom_expected_common_neighbours": expected_common_neighbours,
        "hypergeom_expected_alignment_score": expected_alignment_score,
        "mean_observed_common_neighbours": observed_common_neighbours.mean(),
        "mean_hypergeom_p_value_across_concepts": float(np.mean(p_values)),
        "median_hypergeom_p_value_across_concepts": float(np.median(p_values)),
        "min_hypergeom_p_value_across_concepts": float(np.min(p_values)),
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed_alignment_scores", nargs="+", required=True)
    parser.add_argument("--relabelled_alignment_scores", nargs="+", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--tsv", required=True)
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--number_of_relabelings", type=int, required=True)
    args = parser.parse_args()

    observed_paths_by_model = {}

    for path in args.observed_alignment_scores:
        model = infer_model_from_observed_path(path)
        observed_paths_by_model[model] = path

    relabelled_paths_by_model = {model: [] for model in args.models}

    for path in args.relabelled_alignment_scores:
        model, relabel = infer_model_and_relabel_from_relabelled_path(path)
        relabelled_paths_by_model.setdefault(model, []).append((relabel, path))

    summary_rows = []

    for model in args.models:
        if model not in observed_paths_by_model:
            raise ValueError(f"Missing observed alignment score for model {model}")

        observed_path = observed_paths_by_model[model]
        observed_df = read_alignment_dataframe(observed_path)

        observed_average_alignment = observed_df["alignment_score"].mean()

        hypergeom_stats = compute_hypergeometric_statistics(
            observed_df=observed_df,
            number_of_neighbours=args.number_of_neighbours,
        )

        relabelled_items = sorted(relabelled_paths_by_model.get(model, []))

        if len(relabelled_items) != args.number_of_relabelings:
            raise ValueError(
                f"Model {model} has {len(relabelled_items)} relabelled files, "
                f"but expected {args.number_of_relabelings}."
            )

        null_alignment_scores = []

        for relabel, path in relabelled_items:
            relabelled_df = read_alignment_dataframe(path)
            null_alignment_scores.append(
                relabelled_df["alignment_score"].mean()
            )

        null_alignment_scores = np.array(null_alignment_scores)

        empirical_null_mean = float(null_alignment_scores.mean())
        empirical_null_std = float(null_alignment_scores.std(ddof=1))

        empirical_enrichment = (
            observed_average_alignment / empirical_null_mean
        )

        hypergeom_enrichment = (
            observed_average_alignment
            / hypergeom_stats["hypergeom_expected_alignment_score"]
        )

        hypergeom_null_enrichment = (
            empirical_null_mean
            / hypergeom_stats["hypergeom_expected_alignment_score"]
        )

        z_score_empirical = (
            (observed_average_alignment - empirical_null_mean)
            / empirical_null_std
        )

        empirical_p_value_upper = (
            (np.sum(null_alignment_scores >= observed_average_alignment) + 1)
            / (len(null_alignment_scores) + 1)
        )

        row = {
            "model": model,
            "observed_average_alignment_score": observed_average_alignment,
            "empirical_null_mean_alignment_score": empirical_null_mean,
            "empirical_null_std_alignment_score": empirical_null_std,
            "empirical_enrichment_observed_over_null": empirical_enrichment,
            "empirical_z_score": z_score_empirical,
            "empirical_upper_tail_p_value": empirical_p_value_upper,
            "number_of_relabelings": len(null_alignment_scores),
            "hypergeom_enrichment_observed_over_expected": hypergeom_enrichment,
            "hypergeom_enrichment_null_over_expected": hypergeom_null_enrichment,
        }

        row.update(hypergeom_stats)

        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    tsv_path = Path(args.tsv)
    tsv_path.parent.mkdir(parents=True, exist_ok=True)

    # Long/table format: one row per model.
    summary_df.to_parquet(summary_path, engine="pyarrow", index=False)

    # Wide CSV format: models as columns, metrics as rows.
    summary_wide_df = (
        summary_df
        .set_index("model")
        .transpose()
    )

    summary_wide_df.index.name = None

    summary_wide_df.to_csv(tsv_path, sep="\t")

#    print(summary_wide_df.to_string())

if __name__ == "__main__":
    main()