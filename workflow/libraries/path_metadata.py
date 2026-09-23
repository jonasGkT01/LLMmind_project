from pathlib import Path
import re

LLM_BRAIN_ALIGNMENT_SCORE_PATTERN = re.compile(
    r"dataset-(?P<dataset>.+?)"
    r"_model-(?P<model>.+?)-(?P<stimuli_type>[^_]+)"
    r"_brain_(?P<similarity_type>.+?)"
    r"-alignment_score_(?P<number_of_neighbours>\d+)NN"
    r"\.parquet$"
)

def parse_llm_brain_alignment_score_path(path):
    filename = Path(path).name

    match = LLM_BRAIN_ALIGNMENT_SCORE_PATTERN.fullmatch(filename)

    if match is None:
        raise ValueError(f"Could not parse LLM-brain alignment-score filename: {filename}")

    metadata = match.groupdict()

    metadata["number_of_neighbours"] = int(metadata["number_of_neighbours"])

    return metadata