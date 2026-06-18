#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 INPUT.parquet" >&2
    exit 1
fi

input_file="$1"

if [ ! -f "$input_file" ]; then
    echo "Error: input file '$input_file' does not exist." >&2
    exit 1
fi

if ! command -v duckdb > /dev/null 2>&1; then
    echo "Error: DuckDB is not installed or is not available in PATH." >&2
    exit 1
fi

escaped_input_file=${input_file//\'/\'\'}

duckdb -csv -noheader -c "
    COPY (
        SELECT *
        FROM read_parquet('$escaped_input_file')
    )
    TO '/dev/stdout' (
        FORMAT CSV,
        HEADER,
        DELIMITER E'\t'
    );
"