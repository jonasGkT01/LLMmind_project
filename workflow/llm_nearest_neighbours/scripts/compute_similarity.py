import numpy as np
import pandas as pd

import argparse

# define a function that normalise a vector wrt the l2 norm
def normalize_l2(x):
    x = np.array(x) # convert input to NumPy array
    # check if x is a one-dimensional array
    if x.ndim == 1:
        norm = np.linalg.norm(x) # compute the l2 norm of the vector
        if norm == 0:
            return x
        return x/norm
    # if x is a higher-dimensional array, compute the l2 norm along the columns
    norm = np.linalg.norm(x, 2, axis=1, keepdims=True)
    return np.where(norm == 0, x, x/norm) # short-hand for what has been done for one-dimnensional arrays

def pearson_normalize(x):
    """
    Row-wise Pearson normalization.

    Pearson correlation between two vectors is equivalent to cosine similarity
    after subtracting each vector's mean.
    """
    x = np.asarray(x, dtype=np.float64)

    # mean-center each embedding vector
    x = x - np.mean(x, axis=1, keepdims=True)

    # l2-normalize each centered vector
    x = normalize_l2(x)

    return x

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding_dataframe", 
                      type = str, 
                      help = "Path to dataframe of embeddings")
    parser.add_argument("--cosine_similarity_dataframe", 
                      type = str, 
                      help = "Path to dataframe of computed cosine similarities")
    parser.add_argument("--pearson_similarity_dataframe", 
                      type = str, 
                      help = "Path to dataframe of computed Pearson similarities")
    args = parser.parse_args()

    embedding_dataframe = args.embedding_dataframe
    cosine_similarity_dataframe = args.cosine_similarity_dataframe
    pearson_similarity_dataframe = args.pearson_similarity_dataframe

    # load the dataframe
    embedding_df = pd.read_parquet(args.embedding_dataframe)

    embedding_cols = [
        c for c in embedding_df.columns
        if isinstance(c, int)
    ]

    if not embedding_cols:
        # Parquet may round-trip integer column names as strings depending on engine/version.
        embedding_cols = [
            c for c in embedding_df.columns
            if isinstance(c, str) and c.isdigit()
        ]

    if not embedding_cols:
        raise ValueError(
            f"No embedding columns found. Columns are: {list(embedding_df.columns[:20])}"
        )

    # Sort numerically so dimensions are in order.
    embedding_cols = sorted(embedding_cols, key=lambda c: int(c))

    ##### COSINE SIMILARITY #####
    # compute cosine similarities for all the concepts in the embedding dataframe
    X = normalize_l2(embedding_df[embedding_cols].to_numpy(dtype=np.float64))

    cosine_similarity = X @ X.T

    # remove self-similarities
    np.fill_diagonal(cosine_similarity, -np.inf)

    cosine_similarity_df = pd.DataFrame(
        cosine_similarity, 
        index = embedding_df.index, 
        columns = embedding_df.index
    )
    cosine_similarity_df = cosine_similarity_df.sort_index()

    # save the pandas dataframe as a parquet file
    cosine_similarity_df.to_parquet(cosine_similarity_dataframe, engine="pyarrow", index=True)
    
#    # print the cosine similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(cosine_similarity_df)

    ##### PEARSON SIMILARITY #####
    # compute Pearson similarities for all the concepts in the embedding dataframe
    X = pearson_normalize(embedding_df[embedding_cols].to_numpy(dtype=np.float64))

    pearson_similarity = X @ X.T

    # remove self-similarities
    np.fill_diagonal(pearson_similarity, -np.inf)

    pearson_similarity_df = pd.DataFrame(
        pearson_similarity, 
        index = embedding_df.index, 
        columns = embedding_df.index
    )
    pearson_similarity_df = pearson_similarity_df.sort_index()

    # save the pandas dataframe as a parquet file
    pearson_similarity_df.to_parquet(pearson_similarity_dataframe, engine="pyarrow", index=True)
    
#    # print the pearson similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(pearson_similarity_df)

if __name__ == "__main__":
    main()