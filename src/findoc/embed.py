from __future__ import annotations
from functools import lru_cache
import numpy as np
from FlagEmbedding import BGEM3FlagModel

MODEL_NAME = "BAAI/bge-m3"
DIM = 1024


@lru_cache(maxsize=1)
def get_model() -> BGEM3FlagModel:
    # use_fp16=True: ~1.2GB VRAM, thừa sức cho RTX 4060 8GB
    return BGEM3FlagModel(MODEL_NAME, use_fp16=True)


def embed(texts, batch_size: int = 8, max_length: int = 512) -> np.ndarray:
    """Trả về ma trận (n, 1024) float32 đã chuẩn hóa L2."""
    if isinstance(texts, str):
        texts = [texts]
    out = get_model().encode(texts, batch_size=batch_size, max_length=max_length)
    vecs = np.asarray(out["dense_vecs"], dtype="float32")
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-12, None)
