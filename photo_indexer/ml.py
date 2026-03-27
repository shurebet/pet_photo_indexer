from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image


@dataclass(frozen=True)
class Tag:
    label: str
    score: float
    model: str


def _normalize_model_name(name: str) -> str:
    n = (name or "").strip().lower()
    aliases = {
        "mobilenet": "mobilenet_v3_large",
        "mobilenetv3": "mobilenet_v3_large",
        "mobilenet_v3": "mobilenet_v3_large",
        "resnet": "resnet50",
        "resnet_50": "resnet50",
    }
    return aliases.get(n, n)


@lru_cache(maxsize=2)
def _load_model_and_labels(model_name: str):
    # Lazy import so the rest of the pipeline can run without ML usage.
    import torch
    from torchvision import models

    name = _normalize_model_name(model_name)

    if name == "mobilenet_v3_large":
        weights = models.MobileNet_V3_Large_Weights.DEFAULT
        model = models.mobilenet_v3_large(weights=weights)
    elif name == "resnet50":
        weights = models.ResNet50_Weights.DEFAULT
        model = models.resnet50(weights=weights)
    else:
        raise ValueError(f"Unsupported model: {model_name}. Use 'mobilenet_v3_large' or 'resnet50'.")

    model.eval()
    categories = list(weights.meta.get("categories") or [])
    preprocess = weights.transforms()

    # Keep on CPU by default (works everywhere).
    model.to("cpu")

    return model, preprocess, categories, name, torch


def classify_image(path: Path, *, model_name: str = "mobilenet_v3_large", topk: int = 5) -> List[Tag]:
    model, preprocess, categories, canonical_name, torch = _load_model_and_labels(model_name)

    with Image.open(path) as im:
        im = im.convert("RGB")
        x = preprocess(im).unsqueeze(0)  # 1xCxHxW

    with torch.inference_mode():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)[0]
        k = max(1, int(topk))
        scores, idxs = torch.topk(probs, k=min(k, probs.shape[0]))

    tags: List[Tag] = []
    for score_t, idx_t in zip(scores.tolist(), idxs.tolist(), strict=False):
        label = categories[idx_t] if 0 <= idx_t < len(categories) else str(idx_t)
        tags.append(Tag(label=str(label), score=float(score_t), model=canonical_name))
    return tags


def warmup(model_name: str = "mobilenet_v3_large") -> str:
    """
    Loads the model + weights (and may trigger a one-time download).
    Returns the canonical model name actually used.
    """
    _, _, _, canonical_name, _ = _load_model_and_labels(model_name)
    return canonical_name


def supported_models() -> Sequence[str]:
    return ("mobilenet_v3_large", "resnet50")

