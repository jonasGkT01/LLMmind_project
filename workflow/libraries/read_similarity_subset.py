import json

import pyarrow.parquet as pq

def read_similarity_subset(path, concepts, source):
    """
        Read only the rows/columns needed for `concepts` from a similarity matrix stored as Parquet.

        A similarity matrix can span far more stimuli than a given consumer actually needs (e.g.
        nsd_data's model similarity spans ~66k stimuli while ISC-derived concept sets are limited to the
        ~500 stimuli with enough repetitions), so loading the whole square matrix into memory is
        unnecessary, and at that scale infeasible.
    """
    concepts = [str(concept) for concept in concepts]

    parquet_file = pq.ParquetFile(path)
    schema_names = set(parquet_file.schema_arrow.names)
    pandas_metadata = json.loads(parquet_file.schema_arrow.metadata[b"pandas"])
    index_column = pandas_metadata["index_columns"][0]

    missing_concepts = sorted(set(concepts) - schema_names)

    if missing_concepts:
        raise ValueError(
            f"{source} is missing {len(missing_concepts)} requested concept(s), e.g. {missing_concepts[:5]}"
        )

    table = pq.read_table(path, columns=[index_column, *concepts])
    similarity_df = table.to_pandas(ignore_metadata=True)
    similarity_df = similarity_df.set_index(index_column)

    return similarity_df.loc[concepts, concepts]
