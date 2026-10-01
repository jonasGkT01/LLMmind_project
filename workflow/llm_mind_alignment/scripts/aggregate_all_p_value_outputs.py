#!/usr/bin/env python3
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-01, see docs/changelog/developers/ for details
import argparse
from pathlib import Path
import re

from libraries.aggregate_alignment_scores import aggregate_all_p_value_outputs

# identifies one LLM-brain result, in the order the p-value files are paired up
KEY_COLUMNS = ["dataset", "model", "stimuli_type", "similarity_type", "number_of_neighbours"]
# the same columns in all_model_brain_alignment_scores.tsv's column (and sort) order
METADATA_COLUMNS = ["dataset", "stimuli_type", "similarity_type", "number_of_neighbours", "model"]

def parse_p_value_path(path):
    filename = Path(path).name

    pattern = (
        r"dataset-(?P<dataset>.+?)"
        r"_model-(?P<model>.+?)-(?P<stimuli_type>[^_]+)"
        r"_brain_(?P<method>empirical|hypergeometric)"
        r"_(?P<similarity_type>.+?)"
        r"-alignment_score_(?P<number_of_neighbours>\d+)NN"
        r"\.p_value\.tsv"
    )

    match = re.fullmatch(pattern, filename)

    if match is None:
        raise ValueError(f"Could not parse p-value filename: {path}")

    metadata = match.groupdict()
    metadata["number_of_neighbours"] = int(metadata["number_of_neighbours"])

    return metadata

def parse_relabelled_common_neighbours_path(path):
    filename = Path(path).name

    pattern = (
        r"dataset-(?P<dataset>.+?)"
        r"_model-(?P<model>.+?)-(?P<stimuli_type>[^_]+)"
        r"_brain_(?P<similarity_type>.+?)"
        r"-relabelled_common_neighbours\.parquet"
    )

    match = re.fullmatch(pattern, filename)

    if match is None:
        raise ValueError(f"Could not parse relabelled common-neighbours filename: {path}")

    return match.groupdict()

def main():
    parser = argparse.ArgumentParser(description="Aggregate all concept-level empirical and hypergeometric p-value TSV files into one long model-level summary TSV")
    parser.add_argument("--empirical_p_values",
                        nargs="+",
                        required=True,
                        help="Concept-level empirical p-value TSV files",)
    parser.add_argument("--hypergeometric_p_values",
                        nargs="+",
                        required=True,
                        help="Concept-level hypergeometric p-value TSV files",)
    parser.add_argument("--relabelled_common_neighbours",
                        nargs="+",
                        required=True,
                        help="All-k relabelled common-neighbours Parquet files",)
    parser.add_argument("--all_model_brain_alignment_scores_tsv",
                        required=True,
                        help="Output long model-level summary TSV",)
    parser.add_argument("--threads", 
                        type = int, 
                        required = True, 
                        help = "Number of relabelled files processed in parallel")
    args = parser.parse_args()

    aggregate_all_p_value_outputs(
        empirical_p_values=args.empirical_p_values,
        hypergeometric_p_values=args.hypergeometric_p_values,
        relabelled_common_neighbours=args.relabelled_common_neighbours,
        parse_p_value_path=parse_p_value_path,
        parse_relabelled_common_neighbours_path=parse_relabelled_common_neighbours_path,
        key_columns=KEY_COLUMNS,
        metadata_columns=METADATA_COLUMNS,
        tsv_path=args.all_model_brain_alignment_scores_tsv,
        threads = args.threads,
    )

if __name__ == "__main__":
    main()
