import numpy as np
import pandas as pd
import argparse


def dataframe_to_embedding_matrix(df: pd.DataFrame) -> np.ndarray:
    if df.shape[1] == 1:
        first_col = df.iloc[:, 0]
        is_sequence = first_col.map(lambda v: isinstance(v, (list, tuple, np.ndarray))).all()
        if is_sequence:
            rows = []
            expected_dim = None
            for idx, value in first_col.items():
                arr = np.asarray(value, dtype=np.float64).reshape(-1)
                if expected_dim is None:
                    expected_dim = arr.shape[0]
                elif arr.shape[0] != expected_dim:
                    raise ValueError(
                        f"Inconsistent embedding length for '{idx}': "
                        f"expected {expected_dim}, got {arr.shape[0]}"
                    )
                rows.append(arr)
            return np.vstack(rows)

    try:
        return df.to_numpy(dtype=np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "Embedding dataframe could not be converted to a numeric matrix. "
            "Ensure all embedding values are numeric."
        ) from exc


def normalize_l2(x):
    x = np.asarray(x, dtype=np.float64)

    if x.ndim == 1:
        norm = np.linalg.norm(x)
        if norm == 0:
            return x
        return x / norm

    if x.ndim != 2:
        raise ValueError(f"Expected 1D or 2D array, got {x.ndim}D")

    norm = np.linalg.norm(x, 2, axis=1, keepdims=True)
    return np.divide(x, norm, out=np.zeros_like(x), where=norm != 0)


def pearson_normalize(x):
    """
    Row-wise Pearson normalization.

    Pearson similarity between two vectors is cosine similarity after
    subtracting each vector's mean.
    """
    x = np.asarray(x, dtype=np.float64)

    if x.ndim != 2:
        raise ValueError(f"Expected 2D embedding matrix, got {x.ndim}D")

    # Mean-center each embedding vector
    x = x - np.mean(x, axis=1, keepdims=True)

    # L2-normalize centered vectors
    return normalize_l2(x)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding_isc_dataframe",
                        type=str,
                        help="Path to dataframe of embeddings")
    parser.add_argument("--isc_cosine_similarity_dataframe",
                        type=str,
                        help="Path to dataframe of computed cosine similarities")
    parser.add_argument("--isc_pearson_similarity_dataframe",
                        type=str,
                        help="Path to dataframe of computed Pearson similarities")
    args = parser.parse_args()

    embedding_isc_dataframe = args.embedding_isc_dataframe
    isc_cosine_similarity_dataframe = args.isc_cosine_similarity_dataframe
    isc_pearson_similarity_dataframe = args.isc_pearson_similarity_dataframe

    # load the dataframe
    embedding_df = pd.read_parquet(embedding_isc_dataframe, engine="pyarrow")

    embedding_matrix = dataframe_to_embedding_matrix(embedding_df)

    ##### COSINE SIMILARITY #####
    # compute cosine similarities for all the concepts in the embedding dataframe
    X = normalize_l2(embedding_matrix)
    cosine_result = X @ X.T

    # remove cosine self-similarities
    np.fill_diagonal(cosine_result, np.nan)

    cosine_result_df = pd.DataFrame(
        cosine_result,
        index=embedding_df.index,
        columns=embedding_df.index
    )
    cosine_result_df = cosine_result_df.sort_index()

    # save the pandas dataframe as a parquet file
    cosine_result_df.to_parquet(isc_cosine_similarity_dataframe, engine="pyarrow", index=True)

#    # print the cosine similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(cosine_result_df)

    ##### PEARSON SIMILARITY #####
    # compute Pearson similarities for all concepts in the embedding dataframe
    X = pearson_normalize(embedding_matrix)
    pearson_result = X @ X.T

    # remove Pearson self-similarities
    np.fill_diagonal(pearson_result, np.nan)

    pearson_result_df = pd.DataFrame(
        pearson_result,
        index=embedding_df.index,
        columns=embedding_df.index
    )
    pearson_result_df = pearson_result_df.sort_index()

    # save the pandas dataframe as a parquet file
    pearson_result_df.to_parquet(isc_pearson_similarity_dataframe, engine="pyarrow", index=True)

#    # print the Pearson similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(pearson_result_df)

if __name__ == "__main__":
    main()