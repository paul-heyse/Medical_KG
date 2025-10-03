from __future__ import annotations

from types import SimpleNamespace

import pytest

from Medical_KG.embeddings.gpu import (
    GPURequirementError,
    GPUValidator,
    enforce_gpu_or_exit,
)


@pytest.fixture(autouse=True)
def reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REQUIRE_GPU", raising=False)
    stub = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            mem_get_info=lambda: (1024.0, 2048.0),
        )
    )
    monkeypatch.setattr("Medical_KG.embeddings.gpu.load_torch", lambda: stub)
    monkeypatch.setattr(
        "Medical_KG.embeddings.gpu.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout="gpu0"),
    )


def test_gpu_validator_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    validator = GPUValidator()
    validator.validate()  # does not raise


def test_gpu_validator_raises_without_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "1")
    stub = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    monkeypatch.setattr("Medical_KG.embeddings.gpu.load_torch", lambda: stub)
    validator = GPUValidator()
    with pytest.raises(GPURequirementError):
        validator.validate()


def test_gpu_validator_checks_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "1")
    stub = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            mem_get_info=lambda: (0.0, 0.0),
        )
    )
    monkeypatch.setattr("Medical_KG.embeddings.gpu.load_torch", lambda: stub)
    validator = GPUValidator()
    with pytest.raises(GPURequirementError, match="memory"):
        validator.validate()


def test_gpu_validator_validates_vllm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "1")
    validator = GPUValidator(http_getter=lambda url: 503)
    with pytest.raises(GPURequirementError):
        validator.validate_vllm("http://localhost:8000")


def test_enforce_gpu_or_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingValidator(GPUValidator):
        def validate(self) -> None:  # type: ignore[override]
            raise GPURequirementError("missing gpu")

    with pytest.raises(SystemExit) as excinfo:
        enforce_gpu_or_exit(validator=FailingValidator())
    assert excinfo.value.code == 99
