import numpy as np

def normalize_l2(x):
    x = np.asarray(x, dtype=np.float64)

    if x.ndim == 1:
        norm = np.linalg.norm(x)

        if norm == 0:
            return x

        return x/norm

    if x.ndim != 2:
        raise ValueError(f"Expected 1D or 2D array, got {x.ndim}D")

    norm = np.linalg.norm(x, 2, axis=1, keepdims=True,)

    return np.divide(x, norm, out=np.zeros_like(x), where=norm != 0,)

def pearson_normalize(x):
    x = np.asarray(x, dtype=np.float64)

    if x.ndim != 2:
        raise ValueError(f"Expected 2D embedding matrix, got {x.ndim}D")

    x = x - np.mean(x, axis=1, keepdims=True,)

    return normalize_l2(x)

def cosine_similarity(x):
    x = normalize_l2(x)

    return x @ x.T

def pearson_similarity(x):
    x = pearson_normalize(x)

    return x @ x.T

def dataframe_to_embedding_matrix(embedding_df):
    """Like `extract_embedding_matrix`, but also accepts the ISC dataframe shape: a single column whose
    values are themselves array-like (one brain-response vector per concept) rather than one numeric
    column per dimension."""
    if embedding_df.shape[1] == 1:
        first_col = embedding_df.iloc[:, 0]
        is_sequence = first_col.map(lambda v: isinstance(v, (list, tuple, np.ndarray))).all()

        if is_sequence:
            rows = []
            expected_dim = None

            for idx, value in first_col.items():
                arr = np.asarray(value, dtype=np.float64).reshape(-1)

                if expected_dim is None:
                    expected_dim = arr.shape[0]
                elif arr.shape[0] != expected_dim:
                    raise ValueError(f"Inconsistent embedding length for '{idx}': expected {expected_dim}, got {arr.shape[0]}")

                rows.append(arr)

            return np.vstack(rows)

    try:
        return embedding_df.to_numpy(dtype=np.float64, copy=False)
    except (TypeError, ValueError) as exc:
        raise TypeError("Embedding dataframe could not be converted to a numeric matrix. Ensure all embedding values are numeric") from exc

def extract_embedding_matrix(embedding_df):
    """Pull the numeric embedding-dimension columns out of an embeddings dataframe (whose other columns,
    if any, are non-numeric metadata) as a concepts x dimensions float64 matrix, ordered by dimension."""
    embedding_cols = [c for c in embedding_df.columns if isinstance(c, int)]

    if not embedding_cols:
        # Parquet may round-trip integer column names as strings depending on engine/version.
        embedding_cols = [
            c for c in embedding_df.columns
            if isinstance(c, str) and c.isdigit()
        ]

    if not embedding_cols:
        raise ValueError(f"No embedding columns found. Columns are: {list(embedding_df.columns[:20])}")

    # Sort numerically so dimensions are in order.
    embedding_cols = sorted(embedding_cols, key=lambda c: int(c))

    return embedding_df[embedding_cols].to_numpy(dtype=np.float64)

NORMALIZE_FUNCTIONS_BY_SIMILARITY_TYPE = {
    "cosine": normalize_l2,
    "pearson": pearson_normalize,
}

def normalize_fn_for_similarity_type(similarity_type):
    if similarity_type not in NORMALIZE_FUNCTIONS_BY_SIMILARITY_TYPE:
        raise ValueError(
            f"Unknown similarity_type '{similarity_type}', expected one of "
            f"{sorted(NORMALIZE_FUNCTIONS_BY_SIMILARITY_TYPE)}"
        )

    return NORMALIZE_FUNCTIONS_BY_SIMILARITY_TYPE[similarity_type]