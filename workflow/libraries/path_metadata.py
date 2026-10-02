# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details
from pathlib import Path
import re

# every alignment result file:
# dataset-{d}_model-{m}-{st}_{brain | model-{m2}-{st2}}_[{method}_]{sim}-alignment_score_{k}NN{suffix}
# plus the all-k relabelled file, which has no k:
# dataset-{d}_model-{m}-{st}_{brain | model-{m2}-{st2}}_{sim}-relabelled_common_neighbours.parquet
ALIGNMENT_PATH_PATTERN = re.compile(
    r"dataset-(?P<dataset>.+?)"
    r"_model-(?P<model_1>.+?)-(?P<stimuli_type_1>[^_]+)"
    r"_(?:brain|model-(?P<model_2>.+?)-(?P<stimuli_type_2>[^_]+))"
    r"_(?:(?P<method>empirical|hypergeometric)_)?"
    r"(?P<similarity_type>.+?)"
    r"(?:-alignment_score_(?P<number_of_neighbours>\d+)NN"
    r"(?P<suffix>\.parquet|\.p_value\.tsv)"
    r"|(?P<relabelled>-relabelled_common_neighbours\.parquet))"
)
RELABELLED_SUFFIX = "-relabelled_common_neighbours.parquet"
ISC_TASK_PATTERN = re.compile(r"task-(?P<task>.+)_isc_mean\.npy")

def parse_alignment_path(path):
    # dataset, similarity_type, kind ("score", "p_value" or "relabelled"), number_of_neighbours
    # (int, not for relabelled files) and method (p-value files only); plus model/stimuli_type
    # for LLM-brain files, or model_1/stimuli_type_1/model_2/stimuli_type_2 for LLM-LLM files
    filename = Path(path).name
    match = ALIGNMENT_PATH_PATTERN.fullmatch(filename)

    if match is None:
        raise ValueError(f"Could not parse alignment filename: {filename}")

    metadata = match.groupdict()

    if metadata.pop("relabelled") is not None:
        metadata["kind"] = "relabelled"
    elif metadata["suffix"] == ".parquet":
        metadata["kind"] = "score"
    else:
        metadata["kind"] = "p_value"

    if metadata["model_2"] is None:
        metadata["model"] = metadata.pop("model_1")
        metadata["stimuli_type"] = metadata.pop("stimuli_type_1")

    if metadata["number_of_neighbours"] is not None:
        metadata["number_of_neighbours"] = int(metadata["number_of_neighbours"])

    return {
        key: value
        for key, value in metadata.items()
        if value is not None and key != "suffix"
    }

def relabelled_name_for_observed_path(observed_path, number_of_neighbours):
    # dataset-..._{sim}-alignment_score_{k}NN.parquet -> dataset-..._{sim}-relabelled_common_neighbours.parquet
    observed_name = Path(observed_path).name
    observed_suffix = f"-alignment_score_{number_of_neighbours}NN.parquet"

    if not observed_name.endswith(observed_suffix):
        raise ValueError(
            f"Observed alignment-score filename does not end in {observed_suffix}: "
            f"{observed_name}"
        )

    return observed_name[:-len(observed_suffix)] + RELABELLED_SUFFIX

def parse_isc_task_path(path):
    match = ISC_TASK_PATTERN.fullmatch(Path(path).name)

    if match is None:
        raise ValueError(
            f"Could not parse ISC filename (expected task-<task>_isc_mean.npy): {path}"
        )

    return match.group("task")
