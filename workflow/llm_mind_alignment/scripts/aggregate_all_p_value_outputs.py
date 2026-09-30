#!/usr/bin/env python3
import argparse
from pathlib import Path
import re

from libraries.aggregate_alignment_scores import aggregate_all_p_value_outputs

# identifies one LLM-brain result, in the order the p-value files are paired up
KEY_COLUMNS = ["dataset", "model", "stimuli_type", "similarity_type", "number_of_neighbours"]
# the same columns in all_alignment_scores.tsv's column (and sort) order
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

def parse_relabelled_alignment_score_path(path):
    filename = Path(path).name

    pattern = (
        r"dataset-(?P<dataset>.+?)"
        r"_model-(?P<model>.+?)-(?P<stimuli_type>[^_]+)"
        r"_brain_(?P<similarity_type>.+?)"
        r"-alignment_score_(?P<number_of_neighbours>\d+)NN"
        r"_relabelled\.parquet"
    )

    match = re.fullmatch(pattern, filename)

    if match is None:
        raise ValueError(f"Could not parse relabelled alignment-score filename: {path}")

    metadata = match.groupdict()
    metadata["number_of_neighbours"] = int(metadata["number_of_neighbours"])

    return metadata

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
    parser.add_argument("--relabelled_alignment_scores",
                        nargs="+",
                        required=True,
                        help="Relabelled alignment-score Parquet files",)
    parser.add_argument("--all_alignment_scores_tsv",
                        required=True,
                        help="Output long model-level summary TSV",)
    args = parser.parse_args()

    aggregate_all_p_value_outputs(
        empirical_p_values=args.empirical_p_values,
        hypergeometric_p_values=args.hypergeometric_p_values,
        relabelled_alignment_scores=args.relabelled_alignment_scores,
        parse_p_value_path=parse_p_value_path,
        parse_relabelled_alignment_score_path=parse_relabelled_alignment_score_path,
        key_columns=KEY_COLUMNS,
        metadata_columns=METADATA_COLUMNS,
        tsv_path=args.all_alignment_scores_tsv,
    )

if __name__ == "__main__":
    main()
