"""Register fastembed models not in the built-in supported list."""

from __future__ import annotations

from dataclasses import dataclass

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

_REGISTERED = False


@dataclass(frozen=True)
class CustomEmbeddingSpec:
    model: str
    dim: int
    model_file: str
    size_in_gb: float
    hf_repo: str


# intfloat/multilingual-e5-base is not in TextEmbedding.list_supported_models() yet.
CUSTOM_EMBEDDING_MODELS: dict[str, CustomEmbeddingSpec] = {
    "intfloat/multilingual-e5-base": CustomEmbeddingSpec(
        model="intfloat/multilingual-e5-base",
        dim=768,
        # Quantized ONNX (~555 MB) — smaller image than full fp32 model.onnx (~1.1 GB).
        model_file="onnx/model_O4.onnx",
        size_in_gb=0.55,
        hf_repo="intfloat/multilingual-e5-base",
    ),
}


def register_custom_embedding_models() -> None:
    """Register custom ONNX models with fastembed (idempotent)."""
    global _REGISTERED
    if _REGISTERED:
        return

    supported = {m["model"].lower() for m in TextEmbedding.list_supported_models()}

    for spec in CUSTOM_EMBEDDING_MODELS.values():
        if spec.model.lower() in supported:
            continue
        TextEmbedding.add_custom_model(
            model=spec.model,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf=spec.hf_repo),
            dim=spec.dim,
            model_file=spec.model_file,
            description="Multilingual E5 base (768-dim, query:/passage: prefixes)",
            license="mit",
            size_in_gb=spec.size_in_gb,
            additional_files=[
                "onnx/sentencepiece.bpe.model",
                "onnx/tokenizer.json",
                "onnx/tokenizer_config.json",
                "onnx/special_tokens_map.json",
                "onnx/config.json",
            ],
        )

    _REGISTERED = True
