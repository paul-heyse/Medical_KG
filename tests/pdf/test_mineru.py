import subprocess
from pathlib import Path

import pytest

from Medical_KG.pdf.mineru import MinerUConfig, MinerURunner


class RecordingRunner:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        return subprocess.CompletedProcess(command, self.returncode, stdout="ok", stderr="")


def test_mineru_runner_builds_command_and_paths(tmp_path: Path) -> None:
    config = MinerUConfig(binary="mineru-cli", output_dir=tmp_path)
    runner = RecordingRunner()
    mineru = MinerURunner(config, runner=runner)
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.5")

    result = mineru.run(pdf, "DOC123")

    assert runner.commands[0][0] == "mineru-cli"
    assert result.artifacts.markdown == tmp_path / "DOC123" / "markdown.json"
    assert result.metadata["worker_count"] == 1


def test_mineru_runner_raises_on_failure(tmp_path: Path) -> None:
    config = MinerUConfig(output_dir=tmp_path)
    mineru = MinerURunner(config, runner=RecordingRunner(returncode=1))
    pdf = tmp_path / "broken.pdf"
    pdf.write_bytes(b"%PDF-1.5")

    with pytest.raises(RuntimeError):
        mineru.run(pdf, "FAIL")
