"""Subprocess execution wrapper for email-archiver."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass
class RunResult:
    """Result of an external command execution."""

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def summary(self) -> str:
        status = "OK" if self.ok else f"FAILED (exit {self.exit_code})"
        return f"[{status}] {' '.join(self.command)} ({self.duration_seconds:.1f}s)"


def run_command(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    timeout: float | None = None,
    stream: bool = False,
) -> RunResult:
    """Run an external command and capture its output.

    Args:
        cmd: Command and arguments.
        env: Optional environment variables (merged with current env).
        cwd: Optional working directory.
        timeout: Optional timeout in seconds.
        stream: If True, also print output to stdout/stderr in real time.

    Returns:
        A RunResult with captured output and timing.
    """
    start = time.monotonic()

    try:
        if stream:
            # Stream output in real time while also capturing it
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=cwd,
                text=True,
            )
            stdout_parts: list[str] = []
            stderr_parts: list[str] = []

            # Read stdout line by line
            assert proc.stdout is not None
            assert proc.stderr is not None
            for line in proc.stdout:
                print(line, end="")
                stdout_parts.append(line)
            # Collect remaining stderr
            stderr_data = proc.stderr.read()
            if stderr_data:
                print(stderr_data, end="")
                stderr_parts.append(stderr_data)

            proc.wait(timeout=timeout)
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)
            returncode = proc.returncode
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                cwd=cwd,
                timeout=timeout,
            )
            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode

    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return RunResult(
            command=cmd,
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            duration_seconds=elapsed,
        )
    except FileNotFoundError:
        elapsed = time.monotonic() - start
        return RunResult(
            command=cmd,
            exit_code=-1,
            stdout="",
            stderr=f"Command not found: {cmd[0]}",
            duration_seconds=elapsed,
        )

    elapsed = time.monotonic() - start
    return RunResult(
        command=cmd,
        exit_code=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=elapsed,
    )
