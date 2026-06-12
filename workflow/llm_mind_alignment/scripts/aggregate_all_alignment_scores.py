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
        {model}_brain_{similarity_type}_alignment_score_{number_of_neighbours}NN.parquet
    """
    name = Path(path).name

    match = re.fullmatch(
        r"(.+)_brain_(.+)_alignment_score_(\d+)NN\.parquet",
        name,
    )

    if match is None:
        raise ValueError(f"Cannot infer model from observed path: {path}")

    return match.group(1)

def infer_model_from_relabelled_big_path(path: str) -> str:
    """
        Expected relabelled big path:
        {model}_brain_relabelled_{similarity_type}_alignment_score_{number_of_neighbours}NN.parquet

    Adjust the regex if your filename is different.
    """
    name = Path(path).name

    match = re.fullmatch(
        r"(.+)_brain_relabelled_(.+)_alignment_score_(\d+)NN\.parquet",
        name,
    )

    if match is None:
        raise ValueError(
            f"Cannot infer model from relabelled big alignment path: {path}"
        )

    return match.group(1)

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
    k = number_of_neighbours
    number_of_concepts = len(observed_df)
    population_size = number_of_concepts - 1

    expected_common_neighbours = (k * k) / population_size
    expected_alignment_score = k / population_size

    observed_common_neighbours = observed_df["alignment_score"] * k
    observed_common_neighbours = observed_common_neighbours.round().astype(int)

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

def extract_null_alignment_scores(
    relabelled_df: pd.DataFrame,
) -> np.ndarray:
    if "shuffle_id" in relabelled_df.columns:
        grouped = relabelled_df.groupby("shuffle_id")
    elif "shuffle_id" in relabelled_df.index.names:
        grouped = relabelled_df.groupby(level="shuffle_id")
    else:
        raise ValueError(
            "Expected relabelled alignment dataframe to contain 'shuffle_id' "
            "either as a column or as an index level. "
            f"Columns are: {list(relabelled_df.columns)}. "
            f"Index levels are: {relabelled_df.index.names}."
        )

    null_alignment_scores = []

    for shuffle_id, shuffle_df in grouped:
        null_alignment_scores.append(shuffle_df["alignment_score"].mean())

    return np.array(null_alignment_scores)

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

    relabelled_paths_by_model = {}

    for path in args.relabelled_alignment_scores:
        model = infer_model_from_relabelled_big_path(path)
        relabelled_paths_by_model[model] = path

    summary_rows = []

    for model in args.models:
        if model not in observed_paths_by_model:
            raise ValueError(f"Missing observed alignment score for model {model}")

        if model not in relabelled_paths_by_model:
            raise ValueError(f"Missing relabelled alignment score for model {model}")

        observed_path = observed_paths_by_model[model]
        relabelled_path = relabelled_paths_by_model[model]

        observed_df = read_alignment_dataframe(observed_path)
        relabelled_big_df = read_alignment_dataframe(relabelled_path)

        observed_average_alignment = observed_df["alignment_score"].mean()

        hypergeom_stats = compute_hypergeometric_statistics(
            observed_df=observed_df,
            number_of_neighbours=args.number_of_neighbours,
        )

        null_alignment_scores = extract_null_alignment_scores(
            relabelled_df=relabelled_big_df
        )

        if len(null_alignment_scores) != args.number_of_relabelings:
            raise ValueError(
                f"Model {model} has {len(null_alignment_scores)} relabellings "
                f"in the big dataframe, but expected {args.number_of_relabelings}."
            )

        empirical_null_mean = float(null_alignment_scores.mean())

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

        empirical_p_value_upper = (
            (np.sum(null_alignment_scores >= observed_average_alignment) + 1)
            / (len(null_alignment_scores) + 1)
        )

        row = {
            "model": model,
            "observed_average_number_of_common_neighbours": observed_average_alignment * args.number_of_neighbours,
            "observed_average_alignment_score": observed_average_alignment,
            "empirical_null_mean_alignment_score": empirical_null_mean,
            "empirical_enrichment_observed_over_null": empirical_enrichment,
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

    summary_df.to_parquet(summary_path, engine="pyarrow", index=False)

    summary_wide_df = summary_df.set_index("model").transpose()
    summary_wide_df.index.name = None

    summary_wide_df.to_csv(tsv_path, sep="\t")

if __name__ == "__main__":
    main()