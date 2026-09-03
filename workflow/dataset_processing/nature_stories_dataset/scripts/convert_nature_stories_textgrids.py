from pathlib import Path

from praatio import textgrid

def get_word_tier(tg, input_file):
    """
    Find the word-level interval tier in a TextGrid.

    Prefer tiers named exactly 'word' or 'words', but allow
    other names containing 'word'.
    """
    
    tier_names = list(tg.tierNames)

    for tier_name in tier_names:
        if tier_name.lower() in {"word", "words"}:
            return tg.getTier(tier_name)

    for tier_name in tier_names:
        if "word" in tier_name.lower():
            return tg.getTier(tier_name)

    raise ValueError(f"No word tier found in {input_file}. Available tiers: {tier_names}")

def textgrid_to_txt(input_file, output_file):
    tg = textgrid.openTextgrid(str(input_file), includeEmptyIntervals=True,)

    word_tier = get_word_tier(tg, input_file,)

    BAD_WORDS = {"sentence_start", "sentence_end", "br", "lg", "ls", "ns", "sp",}

    words = []

    for interval in word_tier.entries:
        word = interval.label.strip()

        if not word:
            continue

        normalized_word = (
            word.lower()
            .strip("{}")
            .strip()
        )

        if normalized_word in BAD_WORDS:
            continue

        words.append(word)

    if not words:
        raise ValueError(f"No words were extracted from {input_file}")

    output_file.parent.mkdir(parents=True, exist_ok=True,)

    output_file.write_text(
        " ".join(words) + "\n",
        encoding="utf-8",
    )

    print(f"{input_file.name}: {len(words)} words -> {output_file}")


def main():
    input_files = [
        Path(path)
        for path in snakemake.input.textgrids
    ]

    output_files = [
        Path(path)
        for path in snakemake.output.transcripts
    ]

    if len(input_files) != len(output_files):
        raise ValueError("Number of TextGrids and transcript outputs does not match.")

    for input_file, output_file in zip(input_files, output_files,):
        if not input_file.exists():
            raise FileNotFoundError(f"Missing TextGrid: {input_file}")

        textgrid_to_txt(input_file=input_file, output_file=output_file,)

if __name__ == "__main__":
    main()