import numpy as np
import pandas as pd

from libraries.manage_model_metadata import model_key

def empirical_upper_tail_p_value(number_at_least_as_large, number_of_relabellings,):
    return (number_at_least_as_large + 1)/(number_of_relabellings + 1)

def create_relabelling_rng(random_seed, shuffle_index):
    """A fresh, independently-seeded generator for one relabelling shuffle, so
    that relabellings can be produced in any order (or in parallel) and still
    reproduce the same sequence for a given random_seed."""
    return np.random.default_rng(random_seed + shuffle_index)

def benjamini_hochberg(p_values):
    p_values = np.asarray(p_values, dtype = float,)

    if len(p_values) == 0:
        return np.asarray([], dtype=float)

    order = np.argsort(p_values)
    ordered_p_values = p_values[order]

    ordered_q_values = ordered_p_values*len(p_values)/np.arange(1, len(p_values) + 1,)
    ordered_q_values = np.minimum.accumulate(ordered_q_values[::-1])[::-1]
    q_values = np.empty_like(ordered_q_values)
    q_values[order] = np.minimum(ordered_q_values, 1.0,)

    return q_values

def read_model_level_empirical_p_values(path, dataset, similarity_type, number_of_neighbours):
    # the per-model 'model_level_empirical_p_value' rows of results/all_model_brain_alignment_scores.tsv for one
    # (dataset, similarity type, k), as {model_key(model, stimuli_type): p-value}
    statistics_df = pd.read_csv(path, sep="\t",)

    required_statistic_columns = {"dataset", "stimuli_type", "similarity_type", "number_of_neighbours", "model", "statistic", "value",}

    missing_statistic_columns = required_statistic_columns - set(statistics_df.columns)

    if missing_statistic_columns:
        raise ValueError(f"Model-level statistics file is missing columns: {sorted(missing_statistic_columns)}")

    statistics_df["number_of_neighbours"] = pd.to_numeric(statistics_df["number_of_neighbours"], errors="raise",).astype(int)
    selected_statistics = statistics_df[
        (statistics_df["dataset"].astype(str) == dataset)
        & (statistics_df["similarity_type"].astype(str) == similarity_type)
        & (statistics_df["number_of_neighbours"] == number_of_neighbours)
        & (statistics_df["statistic"].astype(str) == "model_level_empirical_p_value")
    ].copy()

    if selected_statistics.empty:
        raise ValueError(f"No model-level empirical p-values were found for dataset={dataset}, similarity_type={similarity_type}, number_of_neighbours={number_of_neighbours}")

    selected_statistics["value"] = pd.to_numeric(selected_statistics["value"], errors="raise",)

    invalid_p_values = ((selected_statistics["value"] <= 0) | (selected_statistics["value"] > 1))

    if invalid_p_values.any():
        raise ValueError("Model-level statistics contain invalid empirical p-values")

    labels = [
        model_key(model, stimuli_type)
        for model, stimuli_type in zip(selected_statistics["model"].astype(str), selected_statistics["stimuli_type"].astype(str))
    ]

    duplicated_labels = sorted({label for label in labels if labels.count(label) > 1})

    if duplicated_labels:
        raise ValueError(f"More than one model-level empirical p-value was found for: {duplicated_labels}")

    return dict(zip(labels, selected_statistics["value"],))
