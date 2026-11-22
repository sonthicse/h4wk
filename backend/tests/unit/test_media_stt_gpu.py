import pytest

from h4wk.media import stt


def test_stt_requires_cuda(monkeypatch):
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="NVIDIA GPU with CUDA is required"):
        stt._load_model("tiny")
