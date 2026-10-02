# 2026-10-01 — Pinned conda environments

## Changes

- Every package listed in the 11 environment files is pinned to an exact version: conda
  `- pkg=<version>`, pip `netneurotools==0.3.0`, and
  `git+https://github.com/cvnlab/nsdcode.git@bfd36a503cc90a3eb3ebfd69b269403f7e186924` (the current
  HEAD; the only tag, `v1.0`, is older). Versions are the latest on each channel on 2026-10-01
  (`mamba search`), never below the minimum table of TODO P22:
  python 3.14.7, numpy 2.5.3, pandas 3.0.6, pyarrow 25.0.0, scipy 1.18.1, nibabel 5.4.2,
  nilearn 0.14.1, h5py 3.16.0, pip 26.2.1, praatio 6.2.2, git 2.56.0, pillow 12.3.0, tqdm 4.70.1,
  matplotlib 3.11.2, accelerate 1.15.0, bitsandbytes 0.50.2, datasets 5.0.1,
  huggingface_hub 1.32.0, protobuf 7.35.1, pytorch 2.13.0, scikit-learn 1.9.1,
  sentencepiece 0.2.1, tiktoken 0.14.0, timm 1.0.30, torchvision 0.28.0, transformers 5.18.0,
  snakemake 9.27.0.
- `workflow/envs/LLMmind_project_environment.yaml`: `python=3.14.7`, `snakemake=9.27.0`
  (snakemake-minimal 9.27 dropped the `python <3.14` cap of 9.21; snakemake still requires
  `pandas <3`, so this environment resolves pandas 2.3.3; comment added).
- `llm_nearest_neighbours_environment.yaml`: `python=3.12` → `python=3.14.7` (pytorch,
  bitsandbytes, sentencepiece, tiktoken, timm and transformers all solve on 3.14, CUDA 12.9
  builds). New package `cuda-cudart-dev=12.9.79` (approved exception to S22's "no new
  packages"): pytorch 2.13 dispatches some ops (e.g. `bmm_outer_product` in the Gemma rotary
  embedding) to triton kernels; triton compiles a `cuda_utils` helper on first use with
  `-I $CONDA_PREFIX/targets/x86_64-linux/include` and needs `cuda.h`, which no package of the
  environment provided. The current environment only worked because the helper was cached in
  `~/.triton/cache` for cpython-312; a fresh build crashed with `fatal error: cuda.h`.
- `llm_mind_alignment_environment.yaml`: removed `bawk`, `coreutils`, `matrix_reduce` and the
  `molinerislab` channel, used only by the commented-out rules deleted earlier (TODO S29 item 3).
- `README.md`: new "Pinned versions" section (pins, caps, the `cuda-cudart-dev` reason, upgrade
  procedure); the base environment is described as python + full `snakemake`, not
  `snakemake-minimal`.

Release notes checked for breaking changes against the APIs used (`AutoModel`,
`AutoProcessor`, `AutoTokenizer`, `BitsAndBytesConfig`, `snapshot_download`): transformers
5.17 (vision RoPE refactor; not used by DINOv2/CLIP/ViT) and 5.18 (🚨 DINOv2 refactor, PR #46266),
huggingface_hub 1.32. No code change was needed.

## Rerun impact

Every environment file changed, so Snakemake rebuilds every environment and reruns every job. This
change sits on the branch `s22-pinned-envs` and is merged only for the single full recomputation
together with S10, S17 and S31 (and the S7 and S37 branches), as required by the S22 approval.
The base environment `workflow/envs/LLMmind_project/` must be rebuilt by hand at that time:
`conda env create -p workflow/envs/LLMmind_project -f workflow/envs/LLMmind_project_environment.yaml`
after removing the old prefix.

## Verification

- All 11 environments solve (`mamba env create --dry-run`, `CONDA_OVERRIDE_CUDA=12.9`) and build.
- 19 representative jobs, commands from `snakemake -n -p` on `main`, run on the frontend (CPU)
  in the current and in the pinned environment, outputs compared:
  - byte-identical: ISC (Caption Scene, Nature Stories, Narratives), TextGrid conversion,
    `make_nsd_manifest`, Spearman, empirical and hypergeometric p-values;
  - identical values, parquet metadata differs: embeddings of `clip_b`, `dinov2_s` and
    `bloom_560m` (Caption Scene), nearest neighbours (models and ISC), relabelled files;
  - same rows in a different order: the two alignment-score parquets, because
    `compute_alignment_scores()` iterates over a `set` of concepts (string hash randomisation;
    independent of the environment);
  - lineplot: 0 differing pixels.
- node5 GPU, pinned environment with `cuda-cudart-dev`: `get_embeddings.py` for `gemma2_9b`
  (8-bit) and `gemma2_27b` (4-bit) on Narratives gives embeddings exactly equal to the pipeline's.
- Snakemake 9.27.0 (Python 3.14) parses the workflow and builds the DAG without errors.

---

## AI attribution

*This document was written, in whole or in part, with AI coding assistants via Claude Code (Anthropic).*

- *Models: Claude Opus 5.5 (`claude-opus-5-5`).*
- *Latest AI edit: 2026-10-01, Claude Opus 5.5: written for TODO entry S22 (approved by the developer on 2026-09-30; `cuda-cudart-dev` exception approved on 2026-10-01), implemented after the developer chose "Implement S22 (pinning)".*
- *Files changed: all 11 `*_environment.yaml` files (`workflow/envs/`, `workflow/*/envs/`, `workflow/dataset_processing/*/envs/`), `README.md`.*
- *Review status: not yet reviewed by the developer.*
