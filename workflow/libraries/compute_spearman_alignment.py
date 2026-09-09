import numpy as np
from scipy.stats import rankdata

def validate_similarity_dataframe(similarity_df, name):
    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(f"The {name} similarity matrix is not square: shape={similarity_df.shape}")

    if similarity_df.index.has_duplicates:
        raise ValueError(f"The {name} similarity matrix contains duplicate row labels")

    if similarity_df.columns.has_duplicates:
        raise ValueError(f"The {name} similarity matrix contains duplicate column labels")

    concepts = similarity_df.index.to_numpy()
    column_concepts = similarity_df.columns.to_numpy()

    if set(concepts) != set(column_concepts):
        raise ValueError(f"The {name} similarity matrix does not contain the same concepts in its rows and columns")

    similarity_df = similarity_df.loc[concepts, concepts]
    similarity = similarity_df.to_numpy(dtype=np.float64, copy=False)

    if not np.isfinite(similarity).all():
        raise ValueError(f"The {name} similarity matrix contains non-finite values")

    if not np.allclose(similarity, similarity.T, rtol=1e-10, atol=1e-12):
        raise ValueError(f"The {name} similarity matrix is not symmetric")

    return similarity_df

def align_similarity_dataframes(brain_similarity_df, model_similarity_df):
    brain_similarity_df = validate_similarity_dataframe(
        similarity_df=brain_similarity_df,
        name="brain",
    )
    model_similarity_df = validate_similarity_dataframe(
        similarity_df=model_similarity_df,
        name="model",
    )

    brain_concepts = brain_similarity_df.index.to_numpy()
    model_concepts = model_similarity_df.index.to_numpy()
    brain_concept_set = set(brain_concepts)
    model_concept_set = set(model_concepts)

    if brain_concept_set != model_concept_set:
        missing_from_model = sorted(brain_concept_set - model_concept_set, key=str)
        missing_from_brain = sorted(model_concept_set - brain_concept_set, key=str)
        raise ValueError(
            f"Brain and model similarity matrices contain different concepts. "
            f"Missing from model: {missing_from_model}. Missing from brain: {missing_from_brain}"
        )

    if len(brain_concepts) < 3:
        raise ValueError("At least three concepts are required to compute Spearman alignment")

    model_similarity_df = model_similarity_df.loc[brain_concepts, brain_concepts]

    return (
        brain_similarity_df.to_numpy(dtype=np.float64, copy=False),
        model_similarity_df.to_numpy(dtype=np.float64, copy=False),
        brain_concepts,
    )

def normalize_rank_vector(values, name):
    ranks = rankdata(values, method="average")
    ranks = ranks - ranks.mean()
    norm = np.linalg.norm(ranks)

    if norm == 0:
        raise ValueError(f"The {name} similarities have constant ranks")

    return ranks/norm

def rank_upper_triangle(similarity, name):
    row_indices, column_indices = np.triu_indices(similarity.shape[0], k=1)
    rank_geometry = normalize_rank_vector(
        values=similarity[row_indices, column_indices],
        name=name,
    )

    return rank_geometry, row_indices, column_indices

def rank_similarity_rows(similarity, name):
    number_of_concepts = similarity.shape[0]
    concept_indices = np.arange(number_of_concepts)
    rank_matrix = np.zeros_like(similarity, dtype=np.float64)

    for concept_i in range(number_of_concepts):
        other_concepts = concept_indices != concept_i
        rank_matrix[concept_i, other_concepts] = normalize_rank_vector(
            values=similarity[concept_i, other_concepts],
            name=f"{name} concept {concept_i}",
        )

    return rank_matrix