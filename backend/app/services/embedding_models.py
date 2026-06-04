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
    additional_files: tuple[str, ...] = ()


# intfloat/multilingual-e5-base is not built into fastembed yet. The official intfloat
# HF repo uses nested onnx/ paths that trip fastembed's file verification, so we load
# from a flat ONNX port (same E5-base weights, 768-dim, query:/passage: prefixes).
CUSTOM_EMBEDDING_MODELS: dict[str, CustomEmbeddingSpec] = {
    "intfloat/multilingual-e5-base": CustomEmbeddingSpec(
        model="intfloat/multilingual-e5-base",
        dim=768,
        model_file="model_opt2_QInt8.onnx",
        size_in_gb=0.28,
        hf_repo="nixiesearch/multilingual-e5-base-onnx",
        additional_files=("sentencepiece.bpe.model",),
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
            additional_files=list(spec.additional_files),
        )

    _REGISTERED = True
