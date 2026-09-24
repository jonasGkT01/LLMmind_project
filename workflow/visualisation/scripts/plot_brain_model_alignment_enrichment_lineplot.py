#!/usr/bin/env python3
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from libraries.compute_alignment_enrichment import compute_alignment_enrichment, enrichment_ylim
from libraries.compute_statistics import benjamini_hochberg, read_model_level_empirical_p_values
from libraries.manage_model_metadata import model_sort_key, parse_model_parameters
from libraries.visualisation_utils import (
    add_legend,
    add_model_family_annotations,
    ALIGNMENT_ENRICHMENT_LABEL,
    annotate_significance,
    BRAIN_MODEL_ALIGNMENT_ENRICHMENT,
    MODEL_AXIS_LABEL,
    model_figure_width,
    MODEL_LEVEL,
    NULL_STANDARD_DEVIATION,
    plot_title,
    save_model_figure,
    significance_legend_handles,
    style_model_x_axis,
    y_axis_label,
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", nargs="+", required=True, help="Observed LLM-brain alignment score parquet files")
    parser.add_argument("--relabelled_llm_brain_alignment_scores", nargs="+", required=True, help="Relabelled LLM-brain alignment score parquet files, one per observed file")
    parser.add_argument("--model_level_statistics", required=True, help="TSV file containing model-level statistics")
    parser.add_argument("--model_parameters", nargs="+", required=True, help="Model parameter counts formatted as model=parameters_millions")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--similarity_type", required=True)
    parser.add_argument("--number_of_neighbours", type=int, required=True)
    parser.add_argument("--plot", required=True)
    args = parser.parse_args()

    parameters_by_model = parse_model_parameters(args.model_parameters)

    concept_df, model_df = compute_alignment_enrichment(
        observed_paths=args.llm_brain_alignment_scores,
        relabelled_paths=args.relabelled_llm_brain_alignment_scores,
        expected_dataset=args.dataset,
        expected_similarity_type=args.similarity_type,
        expected_number_of_neighbours=args.number_of_neighbours,
    )

    missing_parameters = set(model_df["model"]) - set(parameters_by_model)

    if missing_parameters:
        raise ValueError(f"No number of parameters was provided for models: {sorted(missing_parameters)}")

    model_df = model_df.sort_values(
        "model",
        key=lambda models: models.map(lambda model: model_sort_key(model=model, parameters_by_model=parameters_by_model,)),
    ).reset_index(drop=True)
    models = model_df["model"].tolist()

    p_value_by_model = read_model_level_empirical_p_values(
        path=args.model_level_statistics,
        dataset=args.dataset,
        similarity_type=args.similarity_type,
        number_of_neighbours=args.number_of_neighbours,
    )

    missing_p_values = set(models) - set(p_value_by_model)

    if missing_p_values:
        raise ValueError(f"Missing model-level empirical p-values for models: {sorted(missing_p_values)}")

    p_values = np.asarray([p_value_by_model[model] for model in models], dtype=float,)
    q_values = benjamini_hochberg(p_values)

    output_path = Path(args.plot)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(model_figure_width(len(models)), 7))

    x = style_model_x_axis(ax, models)
    values = model_df["enrichment"].to_numpy(dtype=float)
    errors = model_df["null_standard_deviation"].to_numpy(dtype=float)

    ax.errorbar(x, values, yerr=errors, marker="o", linewidth=1.8, capsize=3,)
    ax.axhline(1.0, linestyle="--", linewidth=1.2, color="grey", label="Null expectation (enrichment = 1)",)

    annotate_significance(ax, x, values + errors, p_values, q_values)
    add_model_family_annotations(ax, models)

    ax.set_xlabel(MODEL_AXIS_LABEL)
    ax.set_ylabel(y_axis_label(ALIGNMENT_ENRICHMENT_LABEL, NULL_STANDARD_DEVIATION))
    ax.set_title(plot_title(MODEL_LEVEL, BRAIN_MODEL_ALIGNMENT_ENRICHMENT, args.dataset, args.similarity_type, args.number_of_neighbours), pad=32)
    ax.set_ylim(*enrichment_ylim(concept_df, model_df))
    add_legend(ax, significance_legend_handles())

    save_model_figure(fig, output_path)

if __name__ == "__main__":
    main()
