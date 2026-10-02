#!/usr/bin/env bash
# edited with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-02, see docs/changelog/developers/ for details

set -euo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 INPUT.parquet" >&2
    exit 1
fi

input_file="$1"

if [[ ! -f "$input_file" ]]; then
    echo "Error: input file '$input_file' does not exist." >&2
    exit 1
fi

if ! command -v duckdb > /dev/null 2>&1; then
    echo "Error: DuckDB is not installed or is not available in PATH." >&2
    exit 1
fi

escaped_input_file="${input_file//\'/\'\'}"

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
