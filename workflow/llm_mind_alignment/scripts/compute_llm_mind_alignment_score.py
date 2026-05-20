import numpy as np
import pandas as pd

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number_of_neighbours", 
                      type = int, 
                      help = "Set the number of neighbours to compute")
    parser.add_argument("--model",
                      type = str,
                      help = "Model for which the alignment score is computed")
    parser.add_argument("--nearest_neighbours_1", 
                      type = str, 
                      help = "Path to dataframe of computed nearest neighbours for the first model")
    parser.add_argument("--nearest_neighbours_2", 
                      type = str, 
                      help = "Path to dataframe of computed nearest neighbours for the second model")
    parser.add_argument("--alignment_score", 
                      type = str, 
                      help = "Path to the file containing the alignment score")
    args = parser.parse_args()

    number_of_neighbours = args.number_of_neighbours
    model = args.model
    nearest_neighbours_1 = args.nearest_neighbours_1
    nearest_neighbours_2 = args.nearest_neighbours_2
    alignment_score = args.alignment_score

    # load the dataframes
    nearest_neighbours_df_1 = pd.read_parquet(nearest_neighbours_1, engine = "pyarrow")
    nearest_neighbours_df_2 = pd.read_parquet(nearest_neighbours_2, engine = "pyarrow")

    # create two dictionaries to store the dataframes of nearest neighbours
    nearest_neighbours_dict_1 = {
        concept: group.drop(columns = "concept").reset_index(drop = True)
        for concept, group in nearest_neighbours_df_1.groupby("concept")
    }
    nearest_neighbours_dict_2 = {
        concept: group.drop(columns = "concept").reset_index(drop = True)
        for concept, group in nearest_neighbours_df_2.groupby("concept")
    }

    # get the set of concepts for which the nearest neighbours in both models have been computed
    concepts = sorted(set(nearest_neighbours_df_1["concept"]) & set(nearest_neighbours_df_2["concept"]))
    rows = []

    # concept by concept, count how many nearest neighbours are in common between the two models
    for c in concepts:
        neighbours_1 = set(nearest_neighbours_dict_1[c]["neighbour"])
        neighbours_2 = set(nearest_neighbours_dict_2[c]["neighbour"])

        try:
            common_neighbours = len(neighbours_1 & neighbours_2)
#            alignment = nearest_neighbours_dict_1[c]["neighbour"].isin(nearest_neighbours_dict_2[c]["neighbour"]).value_counts().get(True, 0)
        except KeyError:
            common_neighbours = np.nan

        rows.append({
            "concept": c, 
            "common_neighbours": common_neighbours, 
            "alignment_score": common_neighbours/number_of_neighbours, 
            "alignment_score_percentage": common_neighbours/number_of_neighbours*100
        })
    
#    number_of_concepts = len(concepts)
#    average_alignment_score = np.nanmean([row["alignment_score"] for row in rows])
#    expected_alignment_score = number_of_neighbours/(number_of_concepts - 1)
#    print(f"Average alignment score with model {model} across all concepts: {average_alignment_score}")
#    print(f"Expected alignment score with model {model} across all concepts: {expected_alignment_score}")
#    print(f"Enrichment of the alignment score with model {model} across all concepts: {average_alignment_score/expected_alignment_score}\n")
    

    # create a pandas datafranme to store alignment scores results
    alignment_score_df = pd.DataFrame(rows).set_index("concept")
    alignment_score_df.index.name = "concept"
    alignment_score_df = alignment_score_df.sort_index()

    # save the nearest neighbours to every concept as a parquet file
    alignment_score_df.to_parquet(alignment_score, engine = "pyarrow", index = True)

#    # print the alignment score dataframe
#    with pd.option_context("display.max_rows", None, "display.max_columns", None):
#        print(alignment_score_df)

if __name__ == "__main__":
    main()