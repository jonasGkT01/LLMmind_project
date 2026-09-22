import numpy as np

REFERENCE_VRAM_GB = 24.0
REFERENCE_SEQUENCE_LENGTH = 512
VISION_BATCH_PARAMETER_BUDGET_MILLIONS = 10_000

QUANTIZATION_MEMORY_MULTIPLIERS = {
    None: 1.0,
    "8bit": 1.5,
    "4bit": 2.0,
}

def suggest_batch_size(
    parameters_millions,
    modality,
    sequence_length = None,
    quantization_method = None,
    available_vram_gb = REFERENCE_VRAM_GB,
    min_batch_size = 1,
    max_batch_size = 256,
):
    """
        Suggest a starting --batch_size from model size instead of a per-model hardcoded constant, so
        new models dropped into config.yaml get a sane default automatically.

        Batch size is taken to scale roughly as 1/parameters, calibrated against these empirical starting
        points for vision transformers on a 24 GB GPU (RTX A5000):
            ~90M params (base ViTs)  -> 64-128
            ~300M params (large)     -> 16-32
            ~630M params (huge)      -> 8-16
            ~1100M params (giant)    -> 4-8
        For language models, cost per sample also scales with sequence length (longer chunks mean more
        activation memory per item), so sequence_length is required and used to scale the same budget.

        This is a starting point, not a guarantee: real activation memory also depends on image
        resolution / architecture details this heuristic does not model. Treat a CUDA out-of-memory error
        as a signal to halve --batch_size, not as a bug in this function.
    """
    if parameters_millions <= 0:
        raise ValueError("parameters_millions must be positive")

    if modality not in ("vision", "language", "multimodal"):
        raise ValueError(f"Unknown modality: {modality}")

    if quantization_method not in QUANTIZATION_MEMORY_MULTIPLIERS:
        raise ValueError(f"Unknown quantization_method: {quantization_method}")

    budget = VISION_BATCH_PARAMETER_BUDGET_MILLIONS*(available_vram_gb/REFERENCE_VRAM_GB)

    if modality in ("language", "multimodal") and sequence_length is not None:
        budget = budget*(REFERENCE_SEQUENCE_LENGTH/sequence_length)

    elif modality == "language":
        raise ValueError("sequence_length is required to size batches for language models")

    budget = budget*QUANTIZATION_MEMORY_MULTIPLIERS[quantization_method]

    raw_batch_size = budget/parameters_millions

    # round down to a power of two: kinder to GPU kernels, and keeps the estimate on the conservative side
    batch_size = 2**int(np.floor(np.log2(max(raw_batch_size, 1))))

    return int(np.clip(batch_size, min_batch_size, max_batch_size))
