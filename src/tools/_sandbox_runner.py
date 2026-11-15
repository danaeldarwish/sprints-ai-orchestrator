"""Trusted runner for the restricted Linux container only.

The application transports this source into a non-root, no-network container.
Static checks and builtins are defense in depth, not the containment boundary.
Direct host invocation is rejected before reading any payload.
"""
import builtins
import json
import os
import sys
import traceback

if os.name != "posix" or os.getuid() != 65534 or os.environ.get("SPRINTS_CONTAINER") != "1":
    raise SystemExit("Container-only runner: a restricted non-root Linux container is required")

# Supplemental per-process address-space ceiling; cgroup RSS controls remain.
# This import is container-only, after the host-execution guard.
import resource
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
# Trusted startup completes before the parent sends any learner payload.
sys.stdout.write("SPRINTS_READY_V1\n")
sys.stdout.flush()

# One bounded UTF-8 JSON frame; never wait for Docker to forward stdin EOF.
MAX_WIRE_BYTES = 512 * 1024
try:
    frame = sys.stdin.buffer.readline(MAX_WIRE_BYTES + 1)
    if len(frame) > MAX_WIRE_BYTES or not frame.endswith(b"\n"):
        raise ValueError("Invalid input frame")
    payload = json.loads(frame.decode("utf-8"))
    if type(payload) is not dict or set(payload) != {"code", "harness", "allowed_modules", "max_output_chars"}:
        raise ValueError("Invalid payload schema")
    if not isinstance(payload["code"], str) or len(payload["code"]) > 20000:
        raise ValueError("Invalid code")
    if not isinstance(payload["harness"], str) or len(payload["harness"]) > 128000:
        raise ValueError("Invalid harness")
    modules = payload["allowed_modules"]
    if type(modules) is not list or len(modules) > 32 or any(type(m) is not str or len(m) > 64 for m in modules):
        raise ValueError("Invalid module list")
    if type(payload["max_output_chars"]) is not int or not 1 <= payload["max_output_chars"] <= 4000:
        raise ValueError("Invalid output bound")
except Exception:
    sys.stderr.write('{"status":"unable_to_verify","source":"python_repl","message":"Sandbox input protocol invalid"}\n')
    sys.stderr.flush()
    raise SystemExit(64)
ALLOWED = set(payload["allowed_modules"])
MAX_OUT = payload["max_output_chars"]
_real_import = builtins.__import__
_real_stdout = sys.stdout


class _Capped:
    """stdout wrapper that hard-stops runaway output instead of buffering it."""

    def __init__(self):
        self.n = 0

    def write(self, s):
        self.n += len(s)
        if self.n > MAX_OUT * 4:
            _real_stdout.write("\n[output limit exceeded]\n")
            _real_stdout.flush()
            os._exit(3)
        return _real_stdout.write(s)

    def flush(self):
        _real_stdout.flush()


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level != 0 or name.split(".")[0] not in ALLOWED:
        raise ImportError(f"import of '{name}' is blocked by the Sprints sandbox")
    return _real_import(name, globals, locals, fromlist, level)


_SAFE = (
    "abs all any ascii bin bool bytearray bytes callable chr classmethod complex dict divmod enumerate filter "
    "float format frozenset hasattr hash hex int isinstance issubclass iter len list map max min next object oct "
    "ord pow print property range repr reversed round set slice sorted staticmethod str sum super tuple type zip "
    "Exception ValueError TypeError KeyError IndexError ZeroDivisionError ArithmeticError AttributeError NameError "
    "RuntimeError StopIteration AssertionError NotImplementedError OverflowError LookupError OSError PermissionError "
    "True False None NotImplemented Ellipsis"
).split()
safe_builtins = {n: getattr(builtins, n) for n in _SAFE}
safe_builtins["__import__"] = _guarded_import
safe_builtins["__build_class__"] = builtins.__build_class__
safe_builtins["__name__"] = "__main__"
ns = {"__builtins__": safe_builtins, "__name__": "__main__"}

sys.stdout = _Capped()


def _fail(exc):
    tb = traceback.extract_tb(exc.__traceback__)
    line = next((f.lineno for f in reversed(tb) if f.filename == "<submission>"), None)
    where = f" (line {line})" if line else ""
    sys.stderr.write(f"{type(exc).__name__}{where}: {exc}\n")
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(1)


try:
    exec(compile(payload["code"], "<submission>", "exec"), ns)
except BaseException as exc:  # noqa: BLE001 - report everything the learner code raised
    _fail(exc)

if payload.get("harness"):
    try:
        exec(compile(payload["harness"], "<harness>", "exec"), ns)
    except BaseException as exc:  # noqa: BLE001
        _fail(exc)
sys.stdout.flush()
