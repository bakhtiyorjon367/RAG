"""Pre-download embedding weights during Docker image build."""

from __future__ import annotations

import os
import sys


def main() -> None:
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


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: embedding bake failed: {exc}", file=sys.stderr, flush=True)
        raise
