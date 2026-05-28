import numpy as np
import pandas as pd

def relabel_wide_similarity(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    relabelled = df.copy()
    concepts = list(df.columns)
    if list(df.index) != concepts:
        raise ValueError(f"Expected the dataframe index to match the columns, but got {list(df.index)} and {concepts}.")
    for concept in concepts:
        other_concepts = [c for c in concepts if c != concept]
        original_values = relabelled.loc[concept, other_concepts].to_numpy()
        shuffled_values = rng.permutation(original_values)
        relabelled.loc[concept, other_concepts] = shuffled_values
        relabelled.loc[concept, concept] = df.loc[concept, concept]
    return relabelled

def compute_nearest_neighbours(sim_df: pd.DataFrame, k: int) -> pd.DataFrame:
    X = sim_df.values
    if X.shape[1] < k + 1:
        raise ValueError(f"Requested number of neighbours {k} is too large for number of concepts {X.shape[1]}.")
    concepts = sim_df.index.to_numpy()
    neighbours = sim_df.columns.to_numpy()
    idx_part = np.argpartition(X, -k, axis=1)[:, -k:]
    scores_part = np.take_along_axis(X, idx_part, axis=1)
    order = np.argsort(scores_part, axis=1)[:, ::-1]
    idx_topk = np.take_along_axis(idx_part, order, axis=1)
    scores_topk = np.take_along_axis(X, idx_topk, axis=1)
    result = pd.DataFrame({
        "concept": np.repeat(concepts, k),
        "neighbour": neighbours[idx_topk.reshape(-1)],
        "similarity": scores_topk.reshape(-1)
    })
    return result
