"""Container-only Sprints Python grading.

AST checks are defense in depth. The application executes no learner code on
the host. Required Linux containment unavailable -> Unable to verify. Actual
Docker enforcement must pass the separate integration tests before any claim
of secure execution. See docs/security_model.md for limits and threat model.
"""
from __future__ import annotations

import ast
import json
import logging
import os
import re
import secrets
import subprocess
import shutil
import tempfile
import threading
import time
import base64
from dataclasses import asdict, dataclass, field
from pathlib import Path

from langchain_core.tools import tool

from src import config
from src.schemas import UnableToVerify

log = logging.getLogger("sprints.repl")
_RUNNER = Path(__file__).with_name("_sandbox_runner.py")

ALLOWED_MODULES = frozenset(
    "math statistics itertools functools collections re json string random datetime heapq bisect typing "
    "dataclasses decimal fractions operator textwrap enum copy __future__".split()
)
BLOCKED_NAMES = frozenset(
    "eval exec compile open input breakpoint exit quit getattr setattr delattr globals locals vars "
    "memoryview help dir __import__ __builtins__ __loader__ __spec__".split()
)


@dataclass
class ReplResult:
    """Outcome of one sandboxed run. ``status`` is ok | runtime_error | timeout | blocked | syntax_error."""

    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: float = 0.0
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def validate_submission(code: str) -> list[str]:
    """Static screening. Returns a list of violations (empty = acceptable). Raises SyntaxError."""
    tree = ast.parse(code)
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_MODULES:
                    problems.append(f"line {node.lineno}: import of '{a.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_MODULES:
                problems.append(f"line {node.lineno}: import from '{node.module}' is not allowed")
        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_NAMES or (node.id.startswith("__") and node.id != "__name__"):
                problems.append(f"line {node.lineno}: use of '{node.id}' is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                problems.append(f"line {node.lineno}: access to private/dunder attribute '{node.attr}' is not allowed")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "__" in node.value and node.value != "__main__":
                problems.append(f"line {node.lineno}: strings containing '__' are not allowed (format-string escape)")
    return problems


class SandboxUnavailable(RuntimeError):
    """Containment cannot be established. Never execute on the host as fallback."""


def _cli_env() -> dict:
    # Do not inherit API keys, Docker endpoint configuration, or proxy secrets.
    return {k: os.environ[k] for k in ("SystemRoot", "WINDIR", "TEMP", "TMP", "PATH") if k in os.environ}


def _docker_prefix(config_dir: str) -> list[str]:
    docker = shutil.which("docker")
    if not docker:
        raise SandboxUnavailable("Docker CLI unavailable")
    endpoint = "npipe:////./pipe/dockerDesktopLinuxEngine" if os.name == "nt" else "unix:///var/run/docker.sock"
    return [docker, "--config", config_dir, "--host", endpoint]


def _control(prefix: list[str], args: list[str], timeout: float = 8) -> subprocess.CompletedProcess:
    return subprocess.run([*prefix, *args], env=_cli_env(), stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def sandbox_capabilities() -> dict:
    """Credential-free local daemon probe, no image download or learner code."""
    try:
        with tempfile.TemporaryDirectory(prefix="sprints-docker-config-") as cfg:
            prefix = _docker_prefix(cfg)
            info = _control(prefix, ["info", "--format", "{{json .}}"])
            if info.returncode:
                raise SandboxUnavailable("Local Linux Docker daemon unavailable")
            data = json.loads(info.stdout)
            if data.get("OSType") != "linux":
                raise SandboxUnavailable("A Linux container daemon is required")
            missing = [k for k in ("MemoryLimit", "SwapLimit", "PidsLimit", "CPUCfsQuota") if not data.get(k)]
            if missing or not any("seccomp" in s for s in data.get("SecurityOptions", [])):
                raise SandboxUnavailable("Required resource controls or seccomp unavailable")
            image = os.getenv("SPRINTS_SANDBOX_IMAGE", "")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
                raise SandboxUnavailable("Configure an approved immutable local image ID (sha256:64hex)")
            check = _control(prefix, ["image", "inspect", image, "--format", "{{json .}}"])
            meta = json.loads(check.stdout) if check.returncode == 0 else {}
            if meta.get("Os") != "linux" or meta.get("Id") != image:
                raise SandboxUnavailable("Approved Linux image is not present locally")
            return {"available": True, "backend": "linux-docker", "image": image,
                    "controls": "no-network,non-root,read-only,no-mounts,seccomp,limits"}
    except Exception as exc:
        return {"available": False, "backend": "linux-docker", "status": "unable_to_verify",
                "reason": str(exc) if isinstance(exc, SandboxUnavailable) else type(exc).__name__}


def _container_args(image: str, name: str, bootstrap: str, timeout_s: float) -> list[str]:
    return ["create", "--name", name, "--pull", "never", "--network", "none", "--user", "65534:65534",
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
            "--memory", f"{config.SANDBOX_MEMORY_MB}m", "--memory-swap", f"{config.SANDBOX_MEMORY_MB}m",
            "--cpus", "0.5", "--pids-limit", "32", "--ulimit", f"cpu={max(1, int(timeout_s))}:{max(1, int(timeout_s))}",
            "--ulimit", "fsize=1048576:1048576", "--ulimit", "core=0:0", "--ulimit", "nofile=64:64",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777", "--workdir", "/tmp",
            "--log-driver", "none", "--init", "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "SPRINTS_CONTAINER=1", "--env", "PYTHONIOENCODING=utf-8",
            "--entrypoint", "python", "-i", image, "-I", "-S", "-c", bootstrap]


def _execute_container(payload: str, timeout_s: float) -> ReplResult:
    capability = sandbox_capabilities()
    if not capability["available"]:
        return ReplResult("unable_to_verify", stderr="Unable to verify: " + capability["reason"])
    runner = base64.b64encode(_RUNNER.read_bytes()).decode("ascii")
    bootstrap = "import base64;exec(compile(base64.b64decode(" + repr(runner) + "),'<trusted-runner>','exec'))"
    name = "sprints-submission-" + secrets.token_hex(12)
    cap = config.SANDBOX_MAX_OUTPUT_CHARS
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="sprints-docker-config-") as cfg:
        prefix = _docker_prefix(cfg)
        created = False
        proc = None
        result = ReplResult("unable_to_verify", stderr="Unable to verify isolated execution")
        try:
            made = _control(prefix, _container_args(capability["image"], name, bootstrap, timeout_s))
            # Cleanup by unpredictable name even if create partially failed.
            created = True
            if made.returncode:
                raise SandboxUnavailable("Required container controls could not be established")
            proc = subprocess.Popen([*prefix, "start", "--attach", "--interactive", name], env=_cli_env(),
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            buffers = [bytearray(), bytearray()]
            overflow = threading.Event()

            def drain(stream, index):
                while True:
                    block = stream.read(1024)
                    if not block:
                        return
                    remaining = cap * 4 - len(buffers[index])
                    if remaining > 0:
                        buffers[index].extend(block[:remaining])
                    if len(block) > remaining:
                        overflow.set()

            readers = [threading.Thread(target=drain, args=(proc.stdout, 0), daemon=True),
                       threading.Thread(target=drain, args=(proc.stderr, 1), daemon=True)]
            for thread in readers:
                thread.start()
            # Feed on a bounded-lifetime thread: a stalled Docker attach must not
            # block the parent before its wall-clock deadline begins.
            def feed():
                try:
                    proc.stdin.write(payload.encode("utf-8"))
                except (BrokenPipeError, OSError):
                    pass
                finally:
                    proc.stdin.close()
            deadline = time.monotonic() + timeout_s
            writer = threading.Thread(target=feed, daemon=True)
            writer.start()
            stopped = ""
            while proc.poll() is None:
                if overflow.is_set() or time.monotonic() >= deadline:
                    stopped = "output_limit" if overflow.is_set() else "timeout"
                    _control(prefix, ["kill", name])
                    break
                time.sleep(0.01)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
            writer.join(timeout=2)
            if writer.is_alive():
                raise SandboxUnavailable("Submission input did not complete")
            for thread in readers:
                thread.join(timeout=2)
            if any(thread.is_alive() for thread in readers):
                raise SandboxUnavailable("Output capture did not complete")
            inspected = _control(prefix, ["inspect", name, "--format", "{{json .State}}"])
            if inspected.returncode:
                raise SandboxUnavailable("Container execution state unavailable")
            state = json.loads(inspected.stdout)
            if state.get("Running") or not isinstance(state.get("ExitCode"), int):
                raise SandboxUnavailable("Container did not stop reliably")
            if overflow.is_set() and not stopped:
                stopped = "output_limit"
            out, err = (b.decode("utf-8", errors="replace")[:cap] for b in buffers)
            status = stopped or ("ok" if state["ExitCode"] == 0 else "runtime_error")
            if state.get("OOMKilled"):
                status, err = "runtime_error", "Memory limit reached (container OOM killed)."
            if state["ExitCode"] == 3:
                status, err = "output_limit", "Output limit exceeded."
            if stopped:
                err = "Output limit exceeded." if stopped == "output_limit" else "Execution time limit exceeded."
            result = ReplResult(status, out, err, state["ExitCode"])
        except Exception as exc:
            result = ReplResult("unable_to_verify", stderr="Unable to verify: " + type(exc).__name__)
        finally:
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
            if created:
                try:
                    removed = _control(prefix, ["rm", "--force", name])
                    if removed.returncode:
                        result = ReplResult("unable_to_verify", stderr="Unable to verify: container cleanup failed")
                except Exception:
                    result = ReplResult("unable_to_verify", stderr="Unable to verify: container cleanup failed")
    result.duration_ms = round((time.perf_counter() - t0) * 1000, 1)
    return result


def run_python_sandboxed(code: str, harness: str = "", timeout_s: float | None = None) -> ReplResult:
    """Execute learner ``code`` (then trusted ``harness``) in the sandbox and capture stdout / errors."""
    timeout_s = config.SANDBOX_TIMEOUT_S if timeout_s is None else timeout_s
    if not 0 < timeout_s <= config.SANDBOX_TIMEOUT_S or len(harness) > 30000:
        return ReplResult("blocked", stderr="Execution request exceeds policy")
    if len(code) > config.SANDBOX_MAX_CODE_CHARS:
        return ReplResult("blocked", violations=[f"submission longer than {config.SANDBOX_MAX_CODE_CHARS} characters"])
    try:
        violations = validate_submission(code)
    except SyntaxError as exc:
        return ReplResult("syntax_error", stderr=f"SyntaxError (line {exc.lineno}): {exc.msg}")
    if violations:
        return ReplResult("blocked", violations=violations, stderr="; ".join(violations))

    payload = json.dumps({"code": code, "harness": harness, "allowed_modules": sorted(ALLOWED_MODULES),
                          "max_output_chars": config.SANDBOX_MAX_OUTPUT_CHARS})
    return _execute_container(payload, timeout_s)


# --------------------------------------------------------- assignment harness
def run_with_tests(code: str, assignment: dict) -> dict:
    """Run ``code`` against an assignment's hidden tests; return evidence for grading.

    The test harness prints its JSON results behind a per-run random nonce that learner code cannot
    know, so a submission cannot fake a passing result by printing one.
    """
    nonce = secrets.token_hex(8) + ":"
    if assignment["kind"] == "function":
        harness = (
            "import json\n_r = []\n"
            f"for _a, _e in {assignment['cases']!r}:\n"
            "    try:\n"
            f"        _g = {assignment['function']}(*_a)\n"
            "        _r.append({'ok': _g == _e, 'input': repr(_a), 'expected': repr(_e), 'got': repr(_g)})\n"
            "    except Exception as _x:\n"
            "        _r.append({'ok': False, 'input': repr(_a), 'expected': repr(_e), 'got': type(_x).__name__ + ': ' + str(_x)})\n"
            f"print({nonce!r} + json.dumps(_r))\n"
        )
    else:
        harness = ""
    run = run_python_sandboxed(code, harness)
    tests: list[dict] = []
    stdout = run.stdout
    if assignment["kind"] == "function" and run.status == "ok":
        lines = stdout.splitlines()
        hit = [ln for ln in lines if ln.startswith(nonce)]
        stdout = "\n".join(ln for ln in lines if not ln.startswith(nonce))
        tests = json.loads(hit[-1][len(nonce):]) if hit else []
    elif assignment["kind"] == "stdout" and run.status == "ok":
        got = [ln.rstrip() for ln in stdout.strip().splitlines()]
        want = assignment["expected_stdout"]
        tests = [{"ok": i < len(got) and got[i] == w, "input": f"line {i + 1}", "expected": w,
                  "got": got[i] if i < len(got) else "<missing>"} for i, w in enumerate(want)]
        if len(got) > len(want):
            tests.append({"ok": False, "input": "extra output", "expected": "<none>", "got": got[len(want)]})
    total = len(tests) or (len(assignment["cases"]) if assignment["kind"] == "function" else len(assignment["expected_stdout"]))
    passed = sum(1 for t in tests if t["ok"])
    return {"run": {**run.to_dict(), "stdout": stdout}, "tests": tests, "passed": passed, "total": total}


@tool
def execute_python(code: str) -> str:
    """Securely execute a Python snippet from a Sprints learner and return its stdout or runtime error as JSON.

    Requires the restricted Linux container (allow-listed imports, 5 s limit, no host mounts or network).
    Unavailable containment returns Unable to verify; there is no host execution fallback.
    Returns {status, stdout, stderr, duration_ms, violations}. On any internal failure returns
    'unable_to_verify' JSON instead of raising. Used by the Assessor Agent for Module 1 assignments.
    """
    try:
        return json.dumps(run_python_sandboxed(code).to_dict())
    except Exception as exc:
        return UnableToVerify(source="python_repl", message="the code could not be executed safely", detail=str(exc)).model_dump_json()
