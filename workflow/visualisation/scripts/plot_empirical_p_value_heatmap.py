#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from libraries.compute_statistics import benjamini_hochberg, model_level_significance
from libraries.manage_model_metadata import (
    model_key, 
    parse_model_parameters, 
    sorted_pairwise_labels, 
)
from libraries.visualisation_utils import (
    EMPIRICAL_P_VALUE_LABEL, 
    PAIRWISE_EMPIRICAL_P_VALUE, 
    PAIRWISE_LEVEL, 
    plot_pairwise_heatmap, 
    plot_title, 
    save_figure, 
    significance_label, 
)

def validate_p_value(value, source):
    p_value = float(value)

    if not 0 < p_value <= 1:
        raise ValueError(f"{source} contains an invalid empirical p-value: {p_value}")

    return p_value

def read_llm_llm_records(path, dataset, similarity_type, number_of_neighbours):
    p_value_df = pd.read_csv(path, sep = "\t")
    pair_columns = ["model_1", "stimuli_type_1", "model_2", "stimuli_type_2"]
    required_columns = {
        "dataset", 
        "similarity_type", 
        "number_of_neighbours", 
        *pair_columns, 
        "statistic", 
        "value"
    }
    missing_columns = required_columns - set(p_value_df.columns)

    if missing_columns:
        raise ValueError(
            f"{path} is missing required columns: {sorted(missing_columns)}"
        )

    p_value_df["number_of_neighbours"] = pd.to_numeric(
        p_value_df["number_of_neighbours"], 
        errors = "raise"
    ).astype(
        int
    )

    selected_df = p_value_df[
        (p_value_df["dataset"].astype(str) == dataset)
        & (p_value_df["similarity_type"].astype(str) == similarity_type)
        & (p_value_df["number_of_neighbours"] == number_of_neighbours)
        & (p_value_df["statistic"].astype(str) == "model_level_empirical_p_value")
    ].copy()

    if selected_df.empty:
        raise ValueError(
            f"No model-model empirical p-values were found in {path} for "
            f"dataset={dataset}, similarity_type={similarity_type}, "
            f"number_of_neighbours={number_of_neighbours}"
        )

    duplicated_rows = selected_df.duplicated(subset = pair_columns, keep = False)

    if duplicated_rows.any():
        duplicates = (
            selected_df.loc[duplicated_rows, pair_columns]
            .drop_duplicates()
            .to_dict(orient = "records")
        )
        raise ValueError(
            f"Duplicated model-model empirical p-values were found: {duplicates[:10]}"
        )

    records = []

    for row in selected_df.itertuples(index = False):
        records.append(
            {
                "model_1": str(row.model_1), 
                "stimuli_type_1": str(row.stimuli_type_1), 
                "model_2": str(row.model_2), 
                "stimuli_type_2": str(row.stimuli_type_2), 
                "empirical_p_value": validate_p_value(row.value, path), 
            }
        )

    return records

def format_p_value(p_value):
    if p_value < 0.0001:
        return "<0.0001"

    return f"{p_value:.4f}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_empirical_p_values", 
                        required = True)
    parser.add_argument("--llm_llm_empirical_p_values", 
                        required = True)
    parser.add_argument("--model_parameters", 
                        nargs = "+", 
                        required = True)
    parser.add_argument("--dataset", 
                        required = True)
    parser.add_argument("--similarity_type", 
                        required = True)
    parser.add_argument("--number_of_neighbours", 
                        type = int, 
                        required = True)
    parser.add_argument("--heatmap", 
                        required = True)
    args = parser.parse_args()

    # model-model cells: one Benjamini-Hochberg family of all pairs of this configuration
    records = read_llm_llm_records(
        path = args.llm_llm_empirical_p_values, 
        dataset = args.dataset, 
        similarity_type = args.similarity_type, 
        number_of_neighbours = args.number_of_neighbours, 
    )
    model_model_q_values = benjamini_hochberg(
        [record["empirical_p_value"] for record in records]
    )
    model_metadata = {}
    pair_values = {}

    for record, q_value in zip(records, model_model_q_values):
        pair_labels = []

        for side in ["1", "2"]:
            model = record[f"model_{side}"]
            stimuli_type = record[f"stimuli_type_{side}"]
            label = model_key(model, stimuli_type)
            model_metadata[label] = {"model": model, "stimuli_type": stimuli_type}
            pair_labels.append(label)

        label_1, label_2 = pair_labels

        if (label_1, label_2) in pair_values or (label_2, label_1) in pair_values:
            raise ValueError(
                f"The empirical p-value for {label_1} and {label_2} was provided more "
                "than once"
            )

        pair_values[(label_1, label_2)] = pair_values[(label_2, label_1)] = (
            record["empirical_p_value"], 
            float(q_value), 
        )

    # brain-model cells: the same family as the brain-model plots, so their asterisks agree
    labels = sorted_pairwise_labels(
        model_metadata, 
        parse_model_parameters(args.model_parameters), 
    )
    model_labels = labels[:-1]
    brain_p_values, brain_q_values = model_level_significance(
        model_labels, 
        args.llm_brain_empirical_p_values, 
        args.dataset, 
        args.similarity_type, 
        args.number_of_neighbours, 
    )

    for label, p_value, q_value in zip(model_labels, brain_p_values, brain_q_values):
        pair_values[(label, "brain")] = (p_value, q_value)
        pair_values[("brain", label)] = (p_value, q_value)

    # colour each cell by -log10(p) and write p and the q-value asterisks in it
    p_value_matrix = np.full((len(labels), len(labels)), np.nan)
    cell_text = [["" for _ in labels] for _ in labels]

    for i, row_label in enumerate(labels):
        for j, column_label in enumerate(labels):
            if (row_label, column_label) in pair_values:
                p_value, q_value = pair_values[(row_label, column_label)]
                p_value_matrix[i, j] = p_value
                cell_text[i][j] = "\n".join(
                    text
                    for text in [format_p_value(p_value), significance_label(q_value)]
                    if text
                )

    transformed_matrix = -np.log10(p_value_matrix)
    finite_values = transformed_matrix[np.isfinite(transformed_matrix)]

    if len(finite_values) == 0:
        raise ValueError("No finite empirical p-values were available for plotting")

    figure_size = max(8, 0.65*len(labels))
    fig, ax = plt.subplots(figsize = (figure_size, figure_size))

    plot_pairwise_heatmap(
        ax, 
        transformed_matrix, 
        cell_text, 
        labels, 
        model_metadata, 
        (0, max(1.0, float(finite_values.max()))), 
        EMPIRICAL_P_VALUE_LABEL, 
    )
    ax.set_title(
        plot_title(
            PAIRWISE_LEVEL, 
            PAIRWISE_EMPIRICAL_P_VALUE, 
            args.dataset, 
            args.similarity_type, 
            args.number_of_neighbours, 
        )
        + "\nasterisks: Benjamini-Hochberg q-value"
    )

    save_figure(fig, args.heatmap, model_figure = False)

if __name__ == "__main__":
    main()
