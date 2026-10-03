"""MEM2-B1b: the worker process has a root log handler at INFO, so its lines reach output.

THE GAP. `arq workers.arq_worker.WorkerSettings` imports this module and THEN runs
dictConfig for the `arq` logger only (arq/cli.py). The root logger was left with no
handler and an effective level of WARNING, so every INFO line the worker wrote through
`workers.*` or `services.*` — including B1's `insight_gate` lines — was dropped before
it reached output.

WHY A SUBPROCESS. `logging.basicConfig` is a no-op when the root already has handlers,
and inside pytest it always does (pytest's own capture handlers), so an in-process
assertion would measure the test runner, not the worker — the 2026-09-01 lesson. The
worker is a fresh interpreter that imports this module; so is the child below. It
performs the import, then arq's real dictConfig in arq's real order, then writes the
two lines that matter and reports what reached its stderr.
"""
import json
import os
import subprocess
import sys

import pytest

API_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHILD = r"""
import json, logging, logging.config, sys
import workers.arq_worker  # the import IS the act under test
from arq.logs import default_log_config
root = logging.getLogger()
state = {
    "root_handlers_after_import": [type(h).__name__ for h in root.handlers],
    "root_level_after_import": logging.getLevelName(root.level),
}
logging.config.dictConfig(default_log_config(False))  # what arq's CLI does next
state["root_handlers_after_arq"] = [type(h).__name__ for h in root.handlers]
state["arq_propagates"] = logging.getLogger("arq").propagate
logging.getLogger("services.memory_service").info(
    "insight_gate kind=%s decision=%s user=%s conv=%s", "recurrence", "allowed", "u", "c")
logging.getLogger("workers.arq_worker").info("Memory task: stored %d entries for user=%s", 2, "u")
logging.getLogger("arq.worker").info("arq internal line")
for h in root.handlers + logging.getLogger("arq").handlers:
    h.flush()
print("STATE " + json.dumps(state))
"""


@pytest.fixture(scope="module")
def worker_process_output():
    env = {**os.environ, "OPENAI_API_KEY": "sk-test-dummy", "ANTHROPIC_API_KEY": "test-dummy"}
    proc = subprocess.run(
        [sys.executable, "-c", CHILD], cwd=API_DIR, env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    state_line = next(l for l in proc.stdout.splitlines() if l.startswith("STATE "))
    return json.loads(state_line[len("STATE "):]), proc.stderr


def test_importing_the_worker_configures_a_root_handler_at_info(worker_process_output):
    state, _ = worker_process_output
    assert state["root_handlers_after_import"] == ["StreamHandler"], state
    assert state["root_level_after_import"] == "INFO", state


def test_arqs_own_dictconfig_does_not_undo_it(worker_process_output):
    """arq's dictConfig has disable_existing_loggers=False and never names the root,
    so the handler survives; and `arq` must not propagate, or its lines print twice."""
    state, _ = worker_process_output
    assert state["root_handlers_after_arq"] == ["StreamHandler"], state
    assert state["arq_propagates"] is False


def test_the_insight_gate_line_reaches_the_worker_output(worker_process_output):
    """The line B1 added for Step 0b, as the worker actually emits it."""
    _, stderr = worker_process_output
    assert "insight_gate kind=recurrence decision=allowed user=u conv=c" in stderr
    assert "Memory task: stored 2 entries for user=u" in stderr


def test_arq_lines_print_once_not_twice(worker_process_output):
    _, stderr = worker_process_output
    assert stderr.count("arq internal line") == 1, stderr
