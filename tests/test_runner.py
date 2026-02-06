"""Tests for email_archiver.runner."""

from __future__ import annotations

from email_archiver.runner import RunResult, run_command


class TestRunResult:
    def test_ok_property(self):
        r = RunResult(command=["true"], exit_code=0, stdout="", stderr="", duration_seconds=0.1)
        assert r.ok is True

    def test_not_ok_property(self):
        r = RunResult(command=["false"], exit_code=1, stdout="", stderr="", duration_seconds=0.1)
        assert r.ok is False

    def test_summary_ok(self):
        r = RunResult(
            command=["echo", "hi"], exit_code=0, stdout="", stderr="", duration_seconds=1.23
        )
        assert "OK" in r.summary()
        assert "1.2s" in r.summary()

    def test_summary_fail(self):
        r = RunResult(command=["fail"], exit_code=2, stdout="", stderr="", duration_seconds=0.5)
        assert "FAILED" in r.summary()
        assert "exit 2" in r.summary()


class TestRunCommand:
    def test_successful_command(self):
        result = run_command(["echo", "hello"])
        assert result.ok
        assert result.stdout.strip() == "hello"
        assert result.exit_code == 0
        assert result.duration_seconds >= 0

    def test_failed_command(self):
        result = run_command(["false"])
        assert not result.ok
        assert result.exit_code != 0

    def test_command_not_found(self):
        result = run_command(["nonexistent_binary_xyz"])
        assert not result.ok
        assert result.exit_code == -1
        assert "not found" in result.stderr.lower()

    def test_captures_stderr(self):
        result = run_command(["sh", "-c", "echo err >&2"])
        assert "err" in result.stderr

    def test_timeout(self):
        result = run_command(["sleep", "10"], timeout=0.1)
        assert not result.ok
        assert result.exit_code == -1
        assert "timed out" in result.stderr.lower()

    def test_captures_duration(self):
        result = run_command(["sleep", "0.1"])
        assert result.duration_seconds >= 0.1
