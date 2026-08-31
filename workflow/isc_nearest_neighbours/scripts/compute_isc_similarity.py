import argparse

import numpy as np
import pandas as pd

from libraries.compute_similarity import cosine_similarity, pearson_similarity

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
                        f"Inconsistent embedding length for '{idx}': expected {expected_dim}, got {arr.shape[0]}"
                    )
                rows.append(arr)
            return np.vstack(rows)

    try:
        return df.to_numpy(dtype=np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "Embedding dataframe could not be converted to a numeric matrix. Ensure all embedding values are numeric"
        ) from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--isc_dataframe",
                        type=str,
                        help="Path to dataframe of ISC's")
    parser.add_argument("--isc_cosine_similarity_dataframe",
                        type=str,
                        help="Path to dataframe of computed cosine similarities")
    parser.add_argument("--isc_pearson_similarity_dataframe",
                        type=str,
                        help="Path to dataframe of computed Pearson similarities")
    args = parser.parse_args()

    isc_dataframe = args.isc_dataframe
    isc_cosine_similarity_dataframe = args.isc_cosine_similarity_dataframe
    isc_pearson_similarity_dataframe = args.isc_pearson_similarity_dataframe

    # load the dataframe
    embedding_df = pd.read_parquet(isc_dataframe, engine="pyarrow")

    embedding_matrix = dataframe_to_embedding_matrix(embedding_df)

    ##### COSINE SIMILARITY #####
    # compute cosine similarities for all the concepts in the embedding dataframe
    cosine_result = cosine_similarity(embedding_matrix)

    cosine_result_df = pd.DataFrame(
        cosine_result,
        index=embedding_df.index,
        columns=embedding_df.index
    )

    # save the pandas dataframe as a parquet file
    cosine_result_df.to_parquet(isc_cosine_similarity_dataframe, engine="pyarrow", index=True)

#    # print the cosine similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(cosine_result_df)

    ##### PEARSON SIMILARITY #####
    # compute Pearson similarities for all concepts in the embedding dataframe
    pearson_result = pearson_similarity(embedding_matrix)

    pearson_result_df = pd.DataFrame(
        pearson_result,
        index=embedding_df.index,
        columns=embedding_df.index
    )

    # save the pandas dataframe as a parquet file
    pearson_result_df.to_parquet(isc_pearson_similarity_dataframe, engine="pyarrow", index=True)

#    # print the Pearson similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(pearson_result_df)

if __name__ == "__main__":
    main()