#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def validate_p_value(value, source):
    p_value = float(value)
    if not 0 < p_value <= 1:
        raise ValueError(f"{source} contains an invalid empirical p-value: {p_value}")
    return p_value

def parse_model_parameters(model_parameters):
    parameters_by_model = {}
    for specification in model_parameters:
        if "=" not in specification:
            raise ValueError(f"Invalid model-parameter specification: {specification}")
        model, number_of_parameters = specification.split("=", 1)
        if model in parameters_by_model:
            raise ValueError(f"Parameters were provided more than once for model {model}")
        parameters_by_model[model] = float(number_of_parameters)
    return parameters_by_model

def model_family(model):
    if "_" not in model:
        return model
    return model.rsplit("_", 1)[0]

def model_label(model, stimuli_type):
    return f"{model}-{stimuli_type}"

def model_sort_key(label, model_metadata):
    if label == "brain":
        return (1, "", "", float("inf"), "")
    metadata = model_metadata[label]
    return (
        0,
        metadata["stimuli_type"],
        model_family(metadata["model"]),
        metadata["number_of_parameters"],
        metadata["model"],
    )

def read_llm_llm_records(paths, parameters_by_model):
    required_columns = {
        "model_1",
        "stimuli_type_1",
        "number_of_parameters_1",
        "model_2",
        "stimuli_type_2",
        "number_of_parameters_2",
        "empirical_p_value",
    }
    records = []
    for path in paths:
        p_value_df = pd.read_csv(path, sep="\t")
        missing_columns = required_columns - set(p_value_df.columns)
        if missing_columns:
            raise ValueError(f"{path} is missing required columns: {sorted(missing_columns)}")
        if len(p_value_df) != 1:
            raise ValueError(f"{path} must contain exactly one row")
        row = p_value_df.iloc[0]
        model_1 = str(row["model_1"])
        model_2 = str(row["model_2"])
        for model, file_parameters in [
            (model_1, float(row["number_of_parameters_1"])),
            (model_2, float(row["number_of_parameters_2"])),
        ]:
            if model not in parameters_by_model:
                raise ValueError(f"No number of parameters was provided for model {model}")
            if not np.isclose(file_parameters, parameters_by_model[model]):
                raise ValueError(
                    f"{path} reports {file_parameters} million parameters for {model}, "
                    f"but the configuration reports {parameters_by_model[model]}"
                )
        records.append(
            {
                "model_1": model_1,
                "stimuli_type_1": str(row["stimuli_type_1"]),
                "model_2": model_2,
                "stimuli_type_2": str(row["stimuli_type_2"]),
                "empirical_p_value": validate_p_value(row["empirical_p_value"], path),
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
    p_value_df["number_of_neighbours"] = pd.to_numeric(
        p_value_df["number_of_neighbours"],
        errors="raise",
    ).astype(int)
    selected_df = p_value_df[
        (p_value_df["dataset"].astype(str) == dataset)
        & (p_value_df["similarity_type"].astype(str) == similarity_type)
        & (p_value_df["number_of_neighbours"] == number_of_neighbours)
        & (p_value_df["statistic"].astype(str) == "model_level_empirical_p_value")
    ].copy()
    if selected_df.empty:
        raise ValueError(
            f"No model-brain empirical p-values were found in {path} for dataset={dataset}, "
            f"similarity_type={similarity_type}, number_of_neighbours={number_of_neighbours}"
        )
    duplicated_rows = selected_df.duplicated(subset=["model", "stimuli_type"], keep=False)
    if duplicated_rows.any():
        duplicates = selected_df.loc[
            duplicated_rows,
            ["model", "stimuli_type"],
        ].drop_duplicates().to_dict(orient="records")
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

def benjamini_hochberg(p_values):
    p_values = np.asarray(p_values, dtype=float)
    if len(p_values) == 0:
        return np.asarray([], dtype=float)
    order = np.argsort(p_values)
    ordered_p_values = p_values[order]
    ordered_q_values = ordered_p_values * len(p_values) / np.arange(1, len(p_values) + 1)
    ordered_q_values = np.minimum.accumulate(ordered_q_values[::-1])[::-1]
    q_values = np.empty_like(ordered_q_values)
    q_values[order] = np.minimum(ordered_q_values, 1.0)
    return q_values

def significance_label(q_value):
    if q_value < 0.001:
        return "***"
    if q_value < 0.01:
        return "**"
    if q_value < 0.05:
        return "*"
    return ""

def format_p_value(p_value):
    if p_value < 0.0001:
        return "<0.0001"
    return f"{p_value:.4f}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_empirical_p_values", required=True)
    parser.add_argument("--llm_llm_empirical_p_values", nargs="+", required=True)
    parser.add_argument("--model_parameters", nargs="+", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--heatmap", required=True)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)
    records = read_llm_llm_records(args.llm_llm_empirical_p_values, parameters_by_model)
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
        label_1 = model_label(record["model_1"], record["stimuli_type_1"])
        label_2 = "brain" if record["model_2"] == "brain" else model_label(
            record["model_2"],
            record["stimuli_type_2"],
        )
        for model, stimuli_type, label in [
            (record["model_1"], record["stimuli_type_1"], label_1),
            (record["model_2"], record["stimuli_type_2"], label_2),
        ]:
            if label == "brain":
                continue
            model_metadata[label] = {
                "model": model,
                "stimuli_type": stimuli_type,
                "number_of_parameters": parameters_by_model[model],
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
        key=lambda label: model_sort_key(label, model_metadata),
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
    figure_size = max(8, 0.65 * len(labels))
    fig, ax = plt.subplots(figsize=(figure_size, figure_size))
    image = ax.imshow(masked_matrix, vmin=0, vmax=max(1.0, float(finite_values.max())))
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=90)
    ax.set_yticklabels(labels)
    for row_i in range(len(labels)):
        for column_i in range(len(labels)):
            p_value = p_value_matrix[row_i, column_i]
            if not np.isfinite(p_value):
                continue
            annotation = format_p_value(p_value)
            significance = significance_label(q_value_matrix[row_i, column_i])
            if significance:
                annotation = f"{annotation}\n{significance}"
            ax.text(column_i, row_i, annotation, ha="center", va="center", fontsize=7)

    ax.set_title("LLM–LLM and LLM–brain empirical p-values")
    ax.set_xlabel("Model / brain")
    ax.set_ylabel("Model / brain")
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("-log10(empirical p-value)")
    fig.tight_layout()
    output_path = Path(args.heatmap)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

if __name__ == "__main__":
    main()