import argparse
from pathlib import Path

import numpy as np
import pandas as pd

def relabel_wide_similarity(
    df: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    """
        Row-wise random permutation of off-diagonal similarities.
        One independent permutaion for each row.
        
        Rows are labelled concepts.
        Columns are candidate concepts.

        For each row/concept:
        - keep the row identity fixed
        - keep the self-comparison fixed
        - randomly permute the similarities to all other concepts

        This destroys the neighbour structure while preserving, for each concept,
        the distribution of similarities to other concepts.
    """

    rng = np.random.default_rng(seed)

    relabelled = df.copy()

    concepts = list(df.columns)
    
    if list(df.index) != concepts:
        raise ValueError(
            f"Expected the dataframe index to match the columns, but got index {list(df.index)} and columns {concepts}."
        )

    for concept in concepts:
        other_concepts = [c for c in concepts if c != concept]

        original_values = relabelled.loc[concept, other_concepts].to_numpy()

        shuffled_values = rng.permutation(original_values)

        relabelled.loc[concept, other_concepts] = shuffled_values

        # Keep self-similarity untouched.
        relabelled.loc[concept, concept] = df.loc[concept, concept]

    return relabelled

def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, required=True)

    args = parser.parse_args()

    df = pd.read_parquet(args.input)

    # Your file appears to be a square wide matrix with concepts as columns.
    # If the index was not saved properly, force it to match the columns.
    if df.shape[0] != df.shape[1]:
        raise ValueError(
            f"Expected a square similarity matrix, but got shape {df.shape}."
        )

    if list(df.index) != list(df.columns):
        df.index = df.columns

    relabelled = relabel_wide_similarity(
        df=df,
        seed=args.seed,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    relabelled.to_parquet(output_path, engine="pyarrow", index=True)

if __name__ == "__main__":
    main()
