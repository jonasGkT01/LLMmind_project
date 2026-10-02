# 2026-10-01 — The model download script takes named options

The script that downloads the pretrained models now takes named options and has a working
`--help`, like the other scripts:

```bash
python3 workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py \
    --model_name bigscience/bloomz-560m \
    --save_dir resources/models/bloom_560m
```

Before, it took the two values without names, and its help message pointed to a folder that no
longer exists. The pipeline calls it for you, so you only need this when downloading a model by
hand.

This change is kept apart and will be added together with the next full rerun of the pipeline,
because it makes Snakemake want to redo every model download and everything after it.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S37, option (b) chosen by the developer on 2026-10-01.*
- *Files changed: `workflow/llm_nearest_neighbours/scripts/download_pretrained_llm.py`, `workflow/llm_nearest_neighbours/Snakefile`.*
- *Review status: not yet reviewed by the developer.*
