#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-01, see docs/changelog/developers/ for details
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from libraries.compute_statistics import benjamini_hochberg
from libraries.manage_model_metadata import model_key, model_sort_key, parse_model_parameters
from libraries.visualisation_utils import colour_tick_labels_by_stimuli_type, contrasting_text_color, EMPIRICAL_P_VALUE_LABEL, PAIRWISE_AXIS_LABEL, PAIRWISE_EMPIRICAL_P_VALUE, PAIRWISE_LEVEL, plot_title, SEQUENTIAL_COLOURMAP, significance_label, stimuli_type_legend_handles

def validate_p_value(value, source):
    p_value = float(value)

    if not 0 < p_value <= 1:
        raise ValueError(f"{source} contains an invalid empirical p-value: {p_value}")
    
    return p_value

def read_llm_llm_records(path, dataset, similarity_type, number_of_neighbours, parameters_by_model):
    p_value_df = pd.read_csv(path, sep="\t")
    pair_columns = ["model_1", "stimuli_type_1", "model_2", "stimuli_type_2"]
    required_columns = {"dataset", "similarity_type", "number_of_neighbours", *pair_columns, "statistic", "value"}
    missing_columns = required_columns - set(p_value_df.columns)

    if missing_columns:
        raise ValueError(f"{path} is missing required columns: {sorted(missing_columns)}")

    p_value_df["number_of_neighbours"] = pd.to_numeric(p_value_df["number_of_neighbours"], errors="raise",).astype(int)

    selected_df = p_value_df[
        (p_value_df["dataset"].astype(str) == dataset)
        & (p_value_df["similarity_type"].astype(str) == similarity_type)
        & (p_value_df["number_of_neighbours"] == number_of_neighbours)
        & (p_value_df["statistic"].astype(str) == "model_level_empirical_p_value")
    ].copy()

    if selected_df.empty:
        raise ValueError(f"No model-model empirical p-values were found in {path} for dataset={dataset}, similarity_type={similarity_type}, number_of_neighbours={number_of_neighbours}")

    duplicated_rows = selected_df.duplicated(subset=pair_columns, keep=False)

    if duplicated_rows.any():
        duplicates = selected_df.loc[duplicated_rows, pair_columns].drop_duplicates().to_dict(orient="records")
        raise ValueError(f"Duplicated model-model empirical p-values were found: {duplicates[:10]}")

    records = []

    for row in selected_df.itertuples(index=False):
        for model in [str(row.model_1), str(row.model_2)]:
            if model not in parameters_by_model:
                raise ValueError(f"No number of parameters was provided for model {model}")

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

def read_llm_brain_records(path, dataset, similarity_type, number_of_neighbours, parameters_by_model):
    p_value_df = pd.read_csv(path, sep="\t")
    required_columns = {
        "dataset",
        "stimuli_type",
        "similarity_type",
        "number_of_neighbours",
        "model",
        "statistic",
        "value",
    }
    missing_columns = required_columns - set(p_value_df.columns)

    if missing_columns:
        raise ValueError(f"{path} is missing required columns: {sorted(missing_columns)}")
    
    p_value_df["number_of_neighbours"] = pd.to_numeric(p_value_df["number_of_neighbours"], errors="raise",).astype(int)

    selected_df = p_value_df[
        (p_value_df["dataset"].astype(str) == dataset)
        & (p_value_df["similarity_type"].astype(str) == similarity_type)
        & (p_value_df["number_of_neighbours"] == number_of_neighbours)
        & (p_value_df["statistic"].astype(str) == "model_level_empirical_p_value")
    ].copy()

    if selected_df.empty:
        raise ValueError(f"No model-brain empirical p-values were found in {path} for dataset={dataset}, similarity_type={similarity_type}, number_of_neighbours={number_of_neighbours}")

    duplicated_rows = selected_df.duplicated(subset=["model", "stimuli_type"], keep=False)

    if duplicated_rows.any():
        duplicates = selected_df.loc[duplicated_rows, ["model", "stimuli_type"],].drop_duplicates().to_dict(orient="records")
        raise ValueError(f"Duplicated model-brain empirical p-values were found: {duplicates[:10]}")

    records = []
    for row in selected_df.itertuples(index=False):
        model = str(row.model)

        if model not in parameters_by_model:
            raise ValueError(f"No number of parameters was provided for model {model}")

        records.append(
            {
                "model_1": model,
                "stimuli_type_1": str(row.stimuli_type),
                "model_2": "brain",
                "stimuli_type_2": None,
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
    parser.add_argument("--llm_brain_empirical_p_values", required=True)
    parser.add_argument("--llm_llm_empirical_p_values", required=True)
    parser.add_argument("--model_parameters", nargs="+", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--heatmap", required=True)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)
    records = read_llm_llm_records(
        path=args.llm_llm_empirical_p_values,
        dataset=args.dataset,
        similarity_type=args.similarity_type,
        number_of_neighbours=args.number_of_neighbours,
        parameters_by_model=parameters_by_model,
    )

    records.extend(
        read_llm_brain_records(
            path=args.llm_brain_empirical_p_values,
            dataset=args.dataset,
            similarity_type=args.similarity_type,
            number_of_neighbours=args.number_of_neighbours,
            parameters_by_model=parameters_by_model,
        )
    )

    q_values = benjamini_hochberg([record["empirical_p_value"] for record in records])
    model_metadata = {}
    pair_values = {}

    for record, q_value in zip(records, q_values):
        label_1 = model_key(record["model_1"], record["stimuli_type_1"])
        label_2 = "brain" if record["model_2"] == "brain" else model_key(record["model_2"], record["stimuli_type_2"])

        for model, stimuli_type, label in [(record["model_1"], record["stimuli_type_1"], label_1), (record["model_2"], record["stimuli_type_2"], label_2),]:
            if label == "brain":
                continue

            model_metadata[label] = {
                "model": model,
                "stimuli_type": stimuli_type,
            }

        if (label_1, label_2) in pair_values or (label_2, label_1) in pair_values:
            raise ValueError(f"The empirical p-value for {label_1} and {label_2} was provided more than once")

        value = {
            "p_value": record["empirical_p_value"],
            "q_value": float(q_value),
        }

        pair_values[(label_1, label_2)] = value
        pair_values[(label_2, label_1)] = value

    labels = sorted(
        set(model_metadata) | {"brain"},
        key = lambda label: (1,) if label == "brain" else (0, *model_sort_key(
            model_metadata[label]["model"],
            model_metadata[label]["stimuli_type"],
            parameters_by_model,
        )),
    )

    p_value_matrix = np.full((len(labels), len(labels)), np.nan)
    q_value_matrix = np.full((len(labels), len(labels)), np.nan)

    for row_i, row_label in enumerate(labels):
        for column_i, column_label in enumerate(labels):
            pair = (row_label, column_label)

            if pair in pair_values:
                p_value_matrix[row_i, column_i] = pair_values[pair]["p_value"]
                q_value_matrix[row_i, column_i] = pair_values[pair]["q_value"]

    transformed_matrix = -np.log10(p_value_matrix)
    finite_values = transformed_matrix[np.isfinite(transformed_matrix)]

    if len(finite_values) == 0:
        raise ValueError("No finite empirical p-values were available for plotting")

    masked_matrix = np.ma.masked_invalid(transformed_matrix)

    output_path = Path(args.heatmap)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure_size = max(8, 0.65 * len(labels))

    fig, ax = plt.subplots(figsize=(figure_size, figure_size))

    image = ax.imshow(masked_matrix, vmin=0, vmax=max(1.0, float(finite_values.max())), cmap=SEQUENTIAL_COLOURMAP)

    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))

    # model names only: the stimulus type is shown by the label colour
    tick_names = [
        label if label == "brain" else model_metadata[label]["model"]
        for label in labels
    ]
    ax.set_xticklabels(tick_names, rotation = 90)
    ax.set_yticklabels(tick_names)

    stimuli_types = [None if label == "brain" else model_metadata[label]["stimuli_type"] for label in labels]
    colour_tick_labels_by_stimuli_type(ax, stimuli_types, axes="xy")

    for row_i in range(len(labels)):
        for column_i in range(len(labels)):
            p_value = p_value_matrix[row_i, column_i]

            if not np.isfinite(p_value):
                continue

            annotation = format_p_value(p_value)
            significance = significance_label(q_value_matrix[row_i, column_i])

            if significance:
                annotation = f"{annotation}\n{significance}"

            transformed_value = transformed_matrix[row_i, column_i]

            text_color = contrasting_text_color(image, transformed_value,)

            ax.text(column_i, row_i, annotation, ha="center", va="center", fontsize=7, color=text_color,)

    ax.set_title(plot_title(PAIRWISE_LEVEL, PAIRWISE_EMPIRICAL_P_VALUE, args.dataset, args.similarity_type, args.number_of_neighbours)
                 + "\nasterisks: Benjamini-Hochberg q-value")
    ax.set_xlabel(PAIRWISE_AXIS_LABEL)
    ax.set_ylabel(PAIRWISE_AXIS_LABEL)

    # fraction/pad size the bar to the square heatmap, so it no longer rises into the title
    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label(EMPIRICAL_P_VALUE_LABEL)

    fig.tight_layout()
    # the bottom-left corner, under the row names, is the only area free of labels
    fig.legend(handles=stimuli_type_legend_handles([stimuli_type for stimuli_type in stimuli_types if stimuli_type is not None]), loc="lower left", fontsize=8, frameon=False,)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

if __name__ == "__main__":
    main()