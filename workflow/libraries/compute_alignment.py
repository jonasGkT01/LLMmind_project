import pandas as pd

def nearest_neighbours_to_dict(nearest_neighbours_df):
    return {
        concept: set(group["neighbour"])
        for concept, group in nearest_neighbours_df.groupby("concept")
    }

def compute_alignment_scores(
    nearest_neighbours_df_1,
    nearest_neighbours_df_2,
    number_of_neighbours,
):
    nearest_neighbours_dict_1 = nearest_neighbours_to_dict(nearest_neighbours_df_1)
    nearest_neighbours_dict_2 = nearest_neighbours_to_dict(nearest_neighbours_df_2)

    concepts = sorted(set(nearest_neighbours_dict_1) & set(nearest_neighbours_dict_2))

    rows = []

    for concept in concepts:
        neighbours_1 = nearest_neighbours_dict_1[concept]
        neighbours_2 = nearest_neighbours_dict_2[concept]

        common_neighbours = len(neighbours_1 & neighbours_2)

        rows.append(
            {
                "concept": concept,
                "common_neighbours": common_neighbours,
                "alignment_score": common_neighbours/number_of_neighbours,
                "alignment_score_percentage": common_neighbours/number_of_neighbours*100,
            }
        )

    return pd.DataFrame(
        rows,
        columns=["concept", "common_neighbours", "alignment_score", "alignment_score_percentage",],
    )

def compute_common_neighbours(
    neighbours,
    neighbour_mask,
    concept_indices,
):
    return neighbour_mask[concept_indices[:, None], neighbours,].sum(axis=1)

def compute_mean_alignment_score(
    neighbour_mask,
    neighbours,
    concept_indices,
    number_of_neighbours,
):
    if neighbour_mask.shape[0] != neighbours.shape[0]:
        raise ValueError(
            "The two nearest-neighbour representations have different numbers of concepts"
        )

    common_neighbours = compute_common_neighbours(neighbours = neighbours, neighbour_mask = neighbour_mask, concept_indices = concept_indices,)

    alignment_scores = common_neighbours/number_of_neighbours

    return float(alignment_scores.mean())