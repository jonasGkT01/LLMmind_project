# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-09, see docs/changelog/developers/ for details
import pandas as pd
import pyarrow.fs

LOCAL_FILESYSTEM = pyarrow.fs.LocalFileSystem()

def read_parquet(path, **read_options):
    # a pyarrow filesystem makes pyarrow open the file itself instead of pandas opening a python
    # file object, whose closing on a pyarrow I/O thread can deadlock the interpreter at exit
    return pd.read_parquet(
        path,
        engine = "pyarrow",
        filesystem = LOCAL_FILESYSTEM,
        **read_options,
    )
