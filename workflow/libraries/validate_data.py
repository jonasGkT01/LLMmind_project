import numpy as np

def validate_required_columns(
    df,
    required_columns,
):
    missing_columns = (set(required_columns) - set(df.columns))

    if missing_columns:
        raise ValueError(
            f"Dataframe is missing required columns: {sorted(missing_columns)}"
        )


def validate_similarity_dataframe(similarity_df,):
    if similarity_df.shape[0] != similarity_df.shape[1]:
        raise ValueError(
            f"Similarity dataframe is not square: shape={similarity_df.shape}"
        )

    if similarity_df.index.has_duplicates:
        raise ValueError(
            f"Similarity dataframe contains duplicate row labels"
        )

    if similarity_df.columns.has_duplicates:
        raise ValueError(
            f"Similarity dataframe contains duplicate column labels"
        )

    row_concepts = list(similarity_df.index)
    column_concepts = list(similarity_df.columns)

    if set(row_concepts) != set(column_concepts):
        raise ValueError(
            f"Similarity dataframe does not contain the same concepts in its rows and columns"
        )

    similarity_df = similarity_df.loc[row_concepts, row_concepts,]

    values = similarity_df.to_numpy()

    if not np.issubdtype(
        values.dtype,
        np.number,
    ):
        raise ValueError(
            f"Similarity dataframe contains non-numeric similarity values"
        )

    if not np.isfinite(values).all():
        raise ValueError(
            f"Similarity dataframe contains non-finite similarity values"
        )

    return similarity_df