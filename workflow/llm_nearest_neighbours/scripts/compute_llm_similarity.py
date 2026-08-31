import argparse

import numpy as np
import pandas as pd

from libraries.compute_similarity import cosine_similarity, pearson_similarity

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

    embedding_cols = [c for c in embedding_df.columns if isinstance(c, int)]

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

    embedding_matrix = embedding_df[embedding_cols].to_numpy(dtype=np.float64)

    ##### COSINE SIMILARITY #####
    # compute cosine similarities for all the concepts in the embedding dataframe
    cosine_result = cosine_similarity(embedding_matrix)

    cosine_similarity_df = pd.DataFrame(
        cosine_result, 
        index = embedding_df.index, 
        columns = embedding_df.index
    )
#    cosine_similarity_df = cosine_similarity_df.sort_index()

    # save the pandas dataframe as a parquet file
    cosine_similarity_df.to_parquet(cosine_similarity_dataframe, engine="pyarrow", index=True)
    
#    # print the cosine similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(cosine_similarity_df)

    ##### PEARSON SIMILARITY #####
    # compute Pearson similarities for all the concepts in the embedding dataframe
    pearson_result = pearson_similarity(embedding_matrix)

    pearson_similarity_df = pd.DataFrame(
        pearson_result, 
        index = embedding_df.index, 
        columns = embedding_df.index
    )
#    pearson_similarity_df = pearson_similarity_df.sort_index()

    # save the pandas dataframe as a parquet file
    pearson_similarity_df.to_parquet(pearson_similarity_dataframe, engine="pyarrow", index=True)
    
#    # print the pearson similarity dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(pearson_similarity_df)

if __name__ == "__main__":
    main()