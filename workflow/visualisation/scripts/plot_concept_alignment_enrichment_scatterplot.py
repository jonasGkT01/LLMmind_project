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
    concept_colours,
    CONCEPT_LEVEL,
    concept_point_alpha,
    deterministic_jitter,
    mark_degenerate_boxplot_statistics,
    MODEL_AXIS_LABEL,
    model_figure_width,
    plot_title,
    save_model_figure,
    significance_legend_handles,
    style_model_x_axis,
    y_axis_label,
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", nargs="+", required=True, help="Observed LLM-brain concept-level alignment-score Parquet files",)
    parser.add_argument("--relabelled_llm_brain_alignment_scores", nargs="+", required=True, help="Relabelled LLM-brain alignment score parquet files, one per observed file",)
    parser.add_argument("--model_level_statistics", required=True, help="TSV file containing model-level statistics",)
    parser.add_argument("--model_parameters", nargs="+", required=True, help="Model parameter counts formatted as model=parameters_millions",)
    parser.add_argument("--dataset", required=True,)
    parser.add_argument("--similarity_type", required=True,)
    parser.add_argument("--number_of_neighbours", type=int, required=True,)
    parser.add_argument("--plot", required=True,)
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

    labels = sorted(
        model_df["label"],
        key=lambda label: model_sort_key(model=label, parameters_by_model=parameters_by_model,),
    )

    p_value_by_model = read_model_level_empirical_p_values(
        path=args.model_level_statistics,
        dataset=args.dataset,
        similarity_type=args.similarity_type,
        number_of_neighbours=args.number_of_neighbours,
    )

    missing_p_values = set(labels) - set(p_value_by_model)

    if missing_p_values:
        raise ValueError(f"Missing model-level empirical p-values for models: {sorted(missing_p_values)}")

    p_values = np.asarray([p_value_by_model[label] for label in labels], dtype=float,)
    q_values = benjamini_hochberg(p_values)

    x_positions = {
        label: position
        for position, label in enumerate(labels)
    }
    boxplot_values = [
        concept_df.loc[concept_df["label"] == label, "enrichment",].to_numpy(dtype=float)
        for label in labels
    ]
    x_values = np.asarray([
        x_positions[row.label] + deterministic_jitter(row.label, str(row.concept), width=0.35)
        for row in concept_df.itertuples(index=False)
    ])

    colour_by_concept = concept_colours(concept_df["concept"])
    colours = concept_df["concept"].map(colour_by_concept).tolist()
    alpha = concept_point_alpha(len(colour_by_concept))
    values = concept_df["enrichment"].to_numpy(dtype=float)

    output_path = Path(args.plot)
    output_path.parent.mkdir(parents=True, exist_ok=True,)

    fig, ax = plt.subplots(figsize=(model_figure_width(len(labels)), 7,))

    style_model_x_axis(ax, labels)
    ax.scatter(x_values, values, s=10, c=colours, alpha=alpha, edgecolors="none", zorder=2,)
    ax.boxplot(boxplot_values,
               positions=range(len(labels)),
               widths=0.55,
               showfliers=False,
               boxprops={"linewidth": 1.5,},
               whiskerprops={"linewidth": 1.5,},
               capprops={"linewidth": 1.5,},
               medianprops={"linewidth": 1.5,},
               zorder=3,)
    mark_degenerate_boxplot_statistics(ax, boxplot_values)
    ax.axhline(1.0, linestyle="--", linewidth=1.2, color="grey", label="Null expectation (enrichment = 1)",)
    add_model_family_annotations(ax, labels)
    annotate_significance(ax, range(len(labels)), p_values, q_values)

    # boxplot() resets the ticks, so restore the model labels
    style_model_x_axis(ax, labels)
    ax.set_ylim(*enrichment_ylim(concept_df, model_df))

    ax.set_title(plot_title(CONCEPT_LEVEL, BRAIN_MODEL_ALIGNMENT_ENRICHMENT, args.dataset, args.similarity_type, args.number_of_neighbours), pad=32,)
    ax.set_xlabel(MODEL_AXIS_LABEL)
    ax.set_ylabel(y_axis_label(ALIGNMENT_ENRICHMENT_LABEL))
    add_legend(ax, significance_legend_handles())

    save_model_figure(fig, output_path)

if __name__ == "__main__":
    main()
