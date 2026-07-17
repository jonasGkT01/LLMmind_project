#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def read_empirical_p_value(path):
    p_value_df = pd.read_csv(
        path,
        sep="\t",
    )

    required_columns = {
        "model_1",
        "stimuli_type_1",
        "number_of_parameters_1",
        "model_2",
        "stimuli_type_2",
        "number_of_parameters_2",
        "empirical_p_value",
    }

    missing_columns = required_columns - set(p_value_df.columns)

    if missing_columns:
        raise ValueError(
            f"{path} is missing required columns: {sorted(missing_columns)}"
        )

    if len(p_value_df) != 1:
        raise ValueError(
            f"{path} must contain exactly one row"
        )

    row = p_value_df.iloc[0]

    empirical_p_value = float(
        row["empirical_p_value"]
    )

    if not 0 < empirical_p_value <= 1:
        raise ValueError(
            f"{path} contains an invalid empirical p-value: {empirical_p_value}"
        )

    return {
        "model_1": str(row["model_1"]),
        "stimuli_type_1": str(
            row["stimuli_type_1"]
        ),
        "number_of_parameters_1": float(
            row["number_of_parameters_1"]
        ),
        "model_2": str(row["model_2"]),
        "stimuli_type_2": str(
            row["stimuli_type_2"]
        ),
        "number_of_parameters_2": float(
            row["number_of_parameters_2"]
        ),
        "empirical_p_value": empirical_p_value,
    }

def model_family(model):
    if "_" not in model:
        return model

    return model.rsplit("_", 1)[0]

def model_label(model, stimuli_type):
    return f"{model}-{stimuli_type}"

def format_p_value(p_value):
    if p_value < 0.0001:
        return "<0.0001"

    return f"{p_value:.4f}"

def benjamini_hochberg(p_values):
    p_values = np.asarray(
        p_values,
        dtype=float,
    )

    number_of_tests = len(p_values)

    if number_of_tests == 0:
        return np.asarray(
            [],
            dtype=float,
        )

    order = np.argsort(p_values)
    ordered_p_values = p_values[order]

    ordered_q_values = ordered_p_values * number_of_tests / np.arange(1, number_of_tests + 1,)

    ordered_q_values = np.minimum.accumulate(ordered_q_values[::-1])[::-1]

    ordered_q_values = np.minimum(ordered_q_values, 1.0,)

    q_values = np.empty_like(ordered_q_values)

    q_values[order] = ordered_q_values

    return q_values

def significance_label(q_value):
    if q_value < 0.001:
        return "***"

    if q_value < 0.01:
        return "**"

    if q_value < 0.05:
        return "*"

    return ""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--empirical_p_values",
        nargs="+",
        required=True,)
    parser.add_argument(
        "--heatmap",
        required=True,)
    args = parser.parse_args()

    records = [
        read_empirical_p_value(path)
        for path in args.empirical_p_values
    ]

    p_values = [
        record["empirical_p_value"]
        for record in records
    ]

    q_values = benjamini_hochberg(
        p_values
    )

    model_metadata = {}
    pair_values = {}

    for record, q_value in zip(
        records,
        q_values,
    ):
        label_1 = model_label(
            model=record["model_1"],
            stimuli_type=record["stimuli_type_1"],
        )

        label_2 = model_label(
            model=record["model_2"],
            stimuli_type=record["stimuli_type_2"],
        )

        model_metadata[label_1] = {
            "model": record["model_1"],
            "stimuli_type": record[
                "stimuli_type_1"
            ],
            "number_of_parameters": record[
                "number_of_parameters_1"
            ],
        }

        model_metadata[label_2] = {
            "model": record["model_2"],
            "stimuli_type": record[
                "stimuli_type_2"
            ],
            "number_of_parameters": record[
                "number_of_parameters_2"
            ],
        }

        pair_values[(label_1, label_2)] = {
            "p_value": record[
                "empirical_p_value"
            ],
            "q_value": float(q_value),
        }

        pair_values[(label_2, label_1)] = {
            "p_value": record[
                "empirical_p_value"
            ],
            "q_value": float(q_value),
        }

    labels = sorted(
        model_metadata,
        key=lambda label: (
            model_metadata[label][
                "stimuli_type"
            ],
            model_family(
                model_metadata[label]["model"]
            ),
            model_metadata[label][
                "number_of_parameters"
            ],
            model_metadata[label]["model"],
        ),
    )

    p_value_matrix = np.full(
        (len(labels), len(labels)),
        np.nan,
    )

    q_value_matrix = np.full(
        (len(labels), len(labels)),
        np.nan,
    )

    for row_i, row_label in enumerate(labels):
        for column_i, column_label in enumerate(
            labels
        ):
            pair = (
                row_label,
                column_label,
            )

            if pair not in pair_values:
                continue

            p_value_matrix[
                row_i,
                column_i,
            ] = pair_values[pair]["p_value"]

            q_value_matrix[
                row_i,
                column_i,
            ] = pair_values[pair]["q_value"]

    transformed_matrix = -np.log10(
        p_value_matrix
    )

    finite_values = transformed_matrix[
        np.isfinite(transformed_matrix)
    ]

    if len(finite_values) == 0:
        raise ValueError(
            "No finite empirical p-values were available for plotting"
        )

    maximum_value = max(
        1.0,
        float(finite_values.max()),
    )

    masked_matrix = np.ma.masked_invalid(
        transformed_matrix
    )

    figure_size = max(
        8,
        0.65 * len(labels),
    )

    fig, ax = plt.subplots(
        figsize=(
            figure_size,
            figure_size,
        )
    )

    image = ax.imshow(
        masked_matrix,
        vmin=0,
        vmax=maximum_value,
    )

    ax.set_xticks(
        np.arange(len(labels))
    )

    ax.set_yticks(
        np.arange(len(labels))
    )

    ax.set_xticklabels(
        labels,
        rotation=90,
    )

    ax.set_yticklabels(labels)

    for row_i in range(len(labels)):
        for column_i in range(len(labels)):
            p_value = p_value_matrix[
                row_i,
                column_i,
            ]

            q_value = q_value_matrix[
                row_i,
                column_i,
            ]

            if not np.isfinite(p_value):
                continue

            annotation = format_p_value(
                p_value
            )

            significance = significance_label(
                q_value
            )

            if significance:
                annotation = (
                    f"{annotation}\n{significance}"
                )

            ax.text(
                column_i,
                row_i,
                annotation,
                ha="center",
                va="center",
                fontsize=7,
            )

    ax.set_title(
        "LLM–LLM empirical p-values"
    )

    ax.set_xlabel("Model")
    ax.set_ylabel("Model")

    colorbar = fig.colorbar(
        image,
        ax=ax,
    )

    colorbar.set_label(
        "-log10(empirical p-value)"
    )

    fig.tight_layout()

    output_path = Path(args.heatmap)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        dpi=300,
    )

    plt.close(fig)

if __name__ == "__main__":
    main()