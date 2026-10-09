# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details
import pandas as pd

from libraries.manage_model_metadata import model_key
from libraries.validate_data import validate_required_columns

NULL_STANDARD_DEVIATION_COLUMN = (
    "empirical_null_standard_deviation_spearman_coefficient"
)

def read_spearman_scores(paths, dataset, model_level):
    # the model-level (model_level = True) or concept-level Spearman TSVs of one dataset,
    # validated, with a label column naming each model and stimulus type
    name = "model-level" if model_level else "concept-level"
    df = pd.concat(
        [
            pd.read_csv(path, sep = "\t")
            for path in paths
        ],
        ignore_index = True,
    )
    required_columns = {
        "dataset",
        "model",
        "stimuli_type",
        "similarity_type",
        "observed_spearman_coefficient",
    }

    if model_level:
        required_columns |= {
            "empirical_upper_tail_p_value",
            NULL_STANDARD_DEVIATION_COLUMN,
        }
    else:
        required_columns.add("concept")

    validate_required_columns(
        df = df,
        required_columns = required_columns,
        source = f"{name} Spearman data"
    )

    if model_level:
        p_values = pd.to_numeric(
            df["empirical_upper_tail_p_value"],
            errors = "coerce"
        )

        if (p_values.isna().any() or (p_values <= 0).any() or (p_values > 1).any()):
            raise ValueError(
                "Model-level Spearman data contains invalid empirical p-values"
            )

        df["empirical_upper_tail_p_value"] = p_values
        null_standard_deviations = pd.to_numeric(
            df[NULL_STANDARD_DEVIATION_COLUMN],
            errors = "coerce",
        )

        if (null_standard_deviations.isna() | (null_standard_deviations < 0)).any():
            raise ValueError(
                "Model-level Spearman data contains invalid null standard "
                "deviations"
            )

        df[NULL_STANDARD_DEVIATION_COLUMN] = null_standard_deviations

    if set(df["dataset"]) != {dataset}:
        raise ValueError(f"{name} Spearman data contains an unexpected dataset")

    coefficients = pd.to_numeric(
        df["observed_spearman_coefficient"],
        errors = "coerce"
    )

    if (
        coefficients.isna().any()
        or ((coefficients < -1) | (coefficients > 1)).any()
    ):
        raise ValueError(f"{name} Spearman data contains invalid coefficients")

    df["observed_spearman_coefficient"] = coefficients
    df["label"] = [
        model_key(model, stimuli_type)
        for model, stimuli_type in zip(
            df["model"].astype(str),
            df["stimuli_type"].astype(str)
        )
    ]

    if model_level and df.duplicated(["label", "similarity_type"]).any():
        raise ValueError(
            "More than one model-level Spearman coefficient was provided for the same "
            "model/stimuli type and similarity type"
        )

    return df
