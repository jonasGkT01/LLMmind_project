import argparse
from pathlib import Path

from praatio.utilities import textgrid_io

BAD_WORDS = {"sentence_start", "sentence_end", "br", "lg", "ls", "ns", "sp",}

def _unquote_praat_string(value):
    value = value.strip()

    if not (value.startswith('"') and value.endswith('"')):
        raise ValueError(
            f"Expected quoted Praat string, got: {value!r}"
        )

    # Praat represents a literal quote inside a string as "".
    return value[1:-1].replace('""', '"')


def parse_chronological_textgrid(data, input_file):
    """
    Parse a Praat chronological TextGrid into the same dictionary-like
    structure returned by praatio.utilities.textgrid_io.parseTextgridStr().

    No IntervalTier objects are constructed, so tiny timestamp overlaps
    in the original Nature Stories annotations are preserved rather than
    rejected.
    """
    lines = [
        line.strip()
        for line in data.splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError(f"Empty TextGrid: {input_file}")

    if lines[0] != '"Praat chronological TextGrid text file"':
        raise ValueError(f"Not a chronological TextGrid: {input_file}")

    # Example:
    # 0.0124716553288 819.988889088   ! Time domain.
    time_tokens = lines[1].split()

    if len(time_tokens) < 2:
        raise ValueError(f"Invalid chronological TextGrid time domain in {input_file}: {lines[1]!r}")

    tg_min = float(time_tokens[0])
    tg_max = float(time_tokens[1])

    # Example:
    # 2   ! Number of tiers.
    n_tiers = int(lines[2].split()[0])

    tiers = []

    # Tier headers immediately follow the global header:
    #
    # "IntervalTier" "phone" 0.012... 819.98...
    # "IntervalTier" "word"  0.012... 819.98...
    for i in range(n_tiers):
        line = lines[3 + i]

        # We know Nature Stories tier names/classes do not contain
        # whitespace, so splitting here is sufficient and transparent.
        parts = line.split()

        if len(parts) < 4:
            raise ValueError(f"Invalid tier header in {input_file}: {line!r}")

        tier_class = _unquote_praat_string(parts[0])
        tier_name = _unquote_praat_string(parts[1])
        tier_min = float(parts[2])
        tier_max = float(parts[3])

        tiers.append(
            {
                "class": tier_class,
                "name": tier_name,
                "xmin": tier_min,
                "xmax": tier_max,
                "entries": [],
            }
        )

    # Remaining lines come in pairs:
    #
    # 1 1.26961451247 1.48948829731937
    # "S"
    #
    # 2 1.26961451247 2.23741496599
    # "SO"
    #
    # The first integer identifies the tier.
    i = 3 + n_tiers

    while i < len(lines):
        timing_line = lines[i]

        if i + 1 >= len(lines):
            raise ValueError(f"Missing label after chronological entry in {input_file}: {timing_line!r}")

        label_line = lines[i + 1]

        parts = timing_line.split()

        if not parts:
            i += 1
            continue

        tier_index = int(parts[0]) - 1

        if tier_index < 0 or tier_index >= len(tiers):
            raise ValueError(f"Invalid tier index {tier_index + 1} in {input_file}")

        tier = tiers[tier_index]
        label = _unquote_praat_string(label_line)

        if tier["class"] == "IntervalTier":
            if len(parts) != 3:
                raise ValueError(f"Invalid interval entry in {input_file}: {timing_line!r}")

            start = float(parts[1])
            end = float(parts[2])

            tier["entries"].append((start, end, label))

        elif tier["class"] == "TextTier":
            if len(parts) != 2:
                raise ValueError(f"Invalid point entry in {input_file}: {timing_line!r}")

            timestamp = float(parts[1])

            tier["entries"].append((timestamp, label))

        else:
            raise ValueError(f"Unsupported tier class {tier['class']!r} in {input_file}")

        i += 2

    return {
        "xmin": tg_min,
        "xmax": tg_max,
        "tiers": tiers,
    }


def read_textgrid(input_file):
    """
    Read both standard ooTextFile TextGrids and chronological
    Nature Stories TextGrids without strict IntervalTier validation.
    """
    raw = input_file.read_bytes()

    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        data = raw.decode("utf-16")
    else:
        data = raw.decode("utf-8-sig")

    data = data.replace("\r\n", "\n").replace("\r", "\n")

    first_nonempty_line = next(
        (
            line.strip()
            for line in data.splitlines()
            if line.strip()
        ),
        "",
    )

    if first_nonempty_line == '"Praat chronological TextGrid text file"':
        return parse_chronological_textgrid(data, input_file,)

    return textgrid_io.parseTextgridStr(data, includeEmptyIntervals=True,)

def get_word_tier(tg, input_file):
    """
    Find the word-level interval tier.

    Prefer explicit word-like tier names. If none exists, use tier 1
    (the second tier), matching the original Huth Nature Stories code.
    """
    tiers = tg["tiers"]

    for tier in tiers:
        tier_name = tier["name"]

        if tier_name.lower() in {"word", "words"}:
            return tier

    for tier in tiers:
        tier_name = tier["name"]

        if "word" in tier_name.lower():
            return tier

    # Original Huth processing uses tiers[1] for the word transcript.
    if len(tiers) > 1:
        return tiers[1]

    tier_names = [tier["name"] for tier in tiers]

    raise ValueError(f"Could not identify word tier in {input_file}. Available tiers: {tier_names}")

def textgrid_to_txt(input_file, output_file):
    tg = read_textgrid(input_file)

    word_tier = get_word_tier(tg, input_file,)

    words = []

    for interval in word_tier["entries"]:
        start, end, label = interval

        word = label.strip()

        if not word:
            continue

        normalized_word = word.lower().strip("{}").strip()

        if normalized_word in BAD_WORDS:
            continue

        words.append(word.lower())

    if not words:
        raise ValueError(f"No words were extracted from {input_file}")

    output_file.parent.mkdir(parents=True, exist_ok=True,)

    output_file.write_text(" ".join(words) + "\n", encoding="utf-8",)

    print(f"{input_file.name}: {len(words)} words -> {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Convert TextGrid files to text transcripts.")
    parser.add_argument("--textgrids", nargs="+", help="Input TextGrid files.")
    parser.add_argument("--transcripts", nargs="+", help="Output transcript files.")
    args = parser.parse_args()

    input_files = [
        Path(path)
        for path in args.textgrids
    ]

    output_files = [
        Path(path)
        for path in args.transcripts
    ]

    if len(input_files) != len(output_files):
        raise ValueError("Number of TextGrids and transcript outputs does not match.")

    for input_file, output_file in zip(input_files, output_files,):
        if not input_file.exists():
            raise FileNotFoundError(f"Missing TextGrid: {input_file}")

        textgrid_to_txt(input_file=input_file, output_file=output_file,)

if __name__ == "__main__":
    main()