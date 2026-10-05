# written with AI assistance: Claude Code, Claude Opus 5.5 (claude-opus-5-5)
# last AI edit: 2026-10-05, see docs/changelog/developers/ for details
import hashlib
import re
from pathlib import Path

LIBRARIES_DIR = Path(__file__).parent
LIBRARY_IMPORT = re.compile(r"^\s*from libraries\.(\w+) import", re.MULTILINE)

def constant_text(constant):
    # frozensets are sorted, since their order changes with the string hash seed
    if hasattr(constant, "co_code"):
        return code_text(constant)

    if isinstance(constant, (tuple, frozenset)):
        items = [constant_text(item) for item in constant]
        return repr(sorted(items) if isinstance(constant, frozenset) else items)

    return repr(constant)

def code_text(code):
    # the instructions, constants and names of a compiled function and of the functions nested
    # in it; comments and line numbers are left out
    return (
        code.co_code.hex()
        + constant_text(code.co_consts)
        + repr(code.co_names)
    )

def script_bytes(path, seen):
    # the script and, recursively, every project library it imports
    seen.add(path)
    content = path.read_bytes()

    for name in LIBRARY_IMPORT.findall(content.decode()):
        library = LIBRARIES_DIR/f"{name}.py"

        if library not in seen:
            content += script_bytes(library, seen)

    return content

def code_version(*items):
    """
        Hash of the code that writes a rule's output: the bytecode of the given
        functions and the content of the given script paths with the project
        libraries they import.

        As a rule param, it reruns the rule when that code changes, which
        Snakemake's own code trigger misses for helper functions defined outside
        a run: block and for scripts called from shell:.
    """
    digest = hashlib.sha256()

    for item in items:
        if callable(item):
            digest.update(code_text(item.__code__).encode())
        else:
            digest.update(script_bytes(Path(item), set()))

    return digest.hexdigest()
