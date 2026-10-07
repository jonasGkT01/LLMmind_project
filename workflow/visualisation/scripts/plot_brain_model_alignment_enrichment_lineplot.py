#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-07, see docs/changelog/developers/ for details
import argparse

from libraries.compute_alignment_enrichment import (
    compute_alignment_enrichment, 
    enrichment_ylim, 
    set_enrichment_y_scale, 
)
from libraries.compute_statistics import model_level_significance
from libraries.manage_model_metadata import parse_model_parameters, sort_models
from libraries.visualisation_utils import (
    add_null_line, 
    ALIGNMENT_ENRICHMENT_LABEL, 
    BRAIN_MODEL_ALIGNMENT_ENRICHMENT, 
    create_model_figure, 
    MODEL_LEVEL, 
    NULL_STANDARD_DEVIATION, 
    plot_model_points, 
    plot_title, 
    save_figure, 
    style_model_axes, 
    y_axis_label, 
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm_brain_alignment_scores", 
                        nargs = "+", 
                        required = True, 
                        help = "Observed LLM-brain alignment score parquet files")
    parser.add_argument("--relabelled_llm_brain_alignment_scores", 
                        nargs = "+", 
                        required = True, 
                        help = "All-k relabelled LLM-brain common-neighbours parquet files, one per observed file")
    parser.add_argument("--model_level_statistics", 
                        required = True, 
                        help = "TSV file containing model-level statistics")
    parser.add_argument("--model_parameters", 
                        nargs = "+", 
                        required = True, 
                        help = "Model parameter counts formatted as model=parameters_millions")
    parser.add_argument("--dataset", 
                        required = True)
    parser.add_argument("--similarity_type", 
                        required = True)
    parser.add_argument("--number_of_neighbours", 
                        type = int, 
                        required = True)
    parser.add_argument("--plot", 
                        required = True)
    args = parser.parse_args()

    # compute the enrichments and the model-level significance
    concept_df, model_df = compute_alignment_enrichment(
        observed_paths = args.llm_brain_alignment_scores, 
        relabelled_paths = args.relabelled_llm_brain_alignment_scores, 
        expected_dataset = args.dataset, 
        expected_similarity_type = args.similarity_type, 
        expected_number_of_neighbours = args.number_of_neighbours, 
    )
    model_df = sort_models(model_df, parse_model_parameters(args.model_parameters))
    p_values, q_values = model_level_significance(
        model_df["label"].tolist(), 
        args.model_level_statistics, 
        args.dataset, 
        args.similarity_type, 
        args.number_of_neighbours, 
    )

    # plot the model enrichments, with each model's null SD as its error bar
    fig, ax = create_model_figure(len(model_df))

    plot_model_points(
        ax, 
        model_df["enrichment"], 
        model_df["null_standard_deviation"], 
        model_df["stimuli_type"], 
    )
    add_null_line(ax, 1.0, "Null expectation (enrichment = 1)")
    style_model_axes(
        ax, 
        model_df["model"].tolist(), 
        model_df["stimuli_type"].tolist(), 
        plot_title(
            MODEL_LEVEL, 
            BRAIN_MODEL_ALIGNMENT_ENRICHMENT, 
            args.dataset, 
            args.similarity_type, 
            args.number_of_neighbours, 
        ), 
        y_axis_label(ALIGNMENT_ENRICHMENT_LABEL, NULL_STANDARD_DEVIATION), 
        p_values, 
        q_values, 
        [], 
    )
    set_enrichment_y_scale(ax)
    ax.set_ylim(*enrichment_ylim(concept_df, model_df))

    save_figure(fig, args.plot)

if __name__ == "__main__":
    main()
