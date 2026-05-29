import numpy as np
import pandas as pd

def relabel_wide_similarity(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    relabelled_df = df.copy()
    concepts = list(df.columns)
    if list(df.index) != concepts:
        raise ValueError(f"Expected the dataframe index to match the columns, but got {list(df.index)} and {concepts}.")

    for concept in concepts:
        other_concepts = [c for c in concepts if c != concept]
        original_values = relabelled_df.loc[concept, other_concepts].to_numpy()
        shuffled_values = rng.permutation(original_values)
        relabelled_df.loc[concept, other_concepts] = shuffled_values
        relabelled_df.loc[concept, concept] = df.loc[concept, concept]

    return relabelled_df

def compute_nearest_neighbours(similarity_df: pd.DataFrame, number_of_neighbours: int) -> pd.DataFrame:
    X = similarity_df.values
    if X.shape[1] < number_of_neighbours + 1:
        raise ValueError(f"Requested number of neighbours {number_of_neighbours} is too large for number of concepts {X.shape[1]}.")
    
    concepts = similarity_df.index.to_numpy()
    neighbours = similarity_df.columns.to_numpy()

    idx_part = np.argpartition(X, -number_of_neighbours, axis=1)[:, -number_of_neighbours:]
    scores_part = np.take_along_axis(X, idx_part, axis=1)
    order = np.argsort(scores_part, axis=1)[:, ::-1]
    idx_topk = np.take_along_axis(idx_part, order, axis=1)
    scores_topk = np.take_along_axis(X, idx_topk, axis=1)
    
    result = pd.DataFrame({
        "concept": np.repeat(concepts, number_of_neighbours),
        "neighbour": neighbours[idx_topk.reshape(-1)],
        "similarity": scores_topk.reshape(-1)
    })

    return result
