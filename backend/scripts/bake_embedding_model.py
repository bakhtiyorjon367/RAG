"""Pre-download model weights during Docker image build (embedding + reranker)."""

from __future__ import annotations

import os
import sys


def bake_embedding() -> None:
    model = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
    cache = os.environ.get("FASTEMBED_CACHE_PATH", "/app/.fastembed_cache")
    os.makedirs(cache, exist_ok=True)
    os.environ["FASTEMBED_CACHE_PATH"] = cache

    from fastembed import TextEmbedding

    from app.services.embedding_models import register_custom_embedding_models

    register_custom_embedding_models()
    print(f"Downloading {model}...", flush=True)
    TextEmbedding(model_name=model)
    print(f"Baked {model}", flush=True)


def bake_reranker() -> None:
    model = os.environ.get("RERANK_MODEL", "ms-marco-MultiBERT-L-12")
    if model == "none":
        print("RERANK_MODEL=none; skipping reranker bake", flush=True)
        return
    cache = os.environ.get("RERANK_CACHE_PATH", "/app/.flashrank_cache")
    os.makedirs(cache, exist_ok=True)

    from flashrank import Ranker

    print(f"Downloading reranker {model}...", flush=True)
    Ranker(model_name=model, max_length=512, cache_dir=cache)
    print(f"Baked reranker {model}", flush=True)


def main() -> None:
    bake_embedding()
    bake_reranker()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: model bake failed: {exc}", file=sys.stderr, flush=True)
        raise
