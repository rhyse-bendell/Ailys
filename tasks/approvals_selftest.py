# tasks/approvals_selftest.py
import datetime
import threading
import core.approval_queue as approvals

def queue_one(timeout_sec: float = 0.5) -> str:
    """
    Enqueue a dummy approval request and return a short status string.
    The GUI can show this status and refresh the approvals list.
    """
    desc = f"SELFTEST approval request @ {datetime.datetime.utcnow().isoformat(timespec='seconds')}Z"

    def _bg():
        approvals.request_approval(description=desc, call_fn=lambda: "ok", timeout=timeout_sec)

    threading.Thread(target=_bg, daemon=True).start()
    return "Queued a self-test approval request. Use 'Refresh Pending Approvals' to see it."
