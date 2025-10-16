import os
import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Any

# --- DEBUG: module identity
import sys as _dbg_sys
print(f"[approval_queue MOD] file={__file__}")


def _env_mode() -> str:
    return (os.getenv("AILYS_APPROVAL_MODE", "manual") or "manual").strip().lower()


@dataclass
class ApprovalRequest:
    id: int
    description: str
    call_fn: Callable[[], Any]
    approved: Optional[bool] = None
    result: Optional[object] = None
    error: Optional[BaseException] = None
    condition: threading.Condition = field(default_factory=threading.Condition)


class ApprovalQueue:
    """
    Modes:
      - manual: queue the request; a GUI (or caller) must approve/deny
      - auto:   execute immediately (no GUI interaction)
      - dryrun: log/track request but do not execute; return None
    """
    def __init__(self, mode: Optional[str] = None):
        self._mode = (mode or _env_mode())
        self._queue: "queue.Queue[ApprovalRequest]" = queue.Queue()
        self._requests: List[ApprovalRequest] = []
        self._next_id = 1
        self._auto_approve_count = 0
        self._lock = threading.RLock()


    # -------- public API -----------------------------------------------------

    def set_mode(self, mode: str):
        self._mode = (mode or "manual").strip().lower()

    def get_mode(self) -> str:
        return self._mode

    def request_approval(
        self,
        description: str,
        call_fn: Callable[[], Any],
        timeout: Optional[float] = None,  # seconds; None = wait forever in manual mode
    ) -> Optional[object]:
        """
        Returns the call result on success, or None if denied/dryrun/failed.
        In manual mode, will block until approved/denied (or until timeout).
        """
        mode = self._mode
        print(f"[request_approval] mode={self._mode} queue_id={id(self)} desc={description!r}")

        # Fast paths: auto / dryrun
        if mode == "auto":
            try:
                print("[request_approval] AUTO mode → executing immediately (no queue)")

                return call_fn()
            except BaseException as e:
                # mirror manual behavior: return None when something goes wrong
                # (error is still captured in the manual path)
                return None

        if mode == "dryrun":
            # track but don't execute
            req = self._enqueue(description, call_fn)
            print(f"[request_approval] DRYRUN mode → enqueued id={req.id}, pending={len(self.get_pending_requests())}")

            req.approved = False  # not executed
            return None

        # Manual mode (with optional N-requests auto-approve burst)
        with self._lock:
            req = self._enqueue(description, call_fn)
            print(f"[request_approval] MANUAL enqueued id={req.id} pending={len(self.get_pending_requests())}")

            if self._auto_approve_count > 0:
                self._auto_approve_count -= 1
                return self._execute_request(req)

        # Block until approved or denied (or timeout)
        with req.condition:
            print(f"[request_approval] waiting on condition (timeout={timeout}) for id={req.id}")
            # wait until approved is no longer None, or until timeout expires
            if timeout is None:
                while req.approved is None:
                    req.condition.wait(timeout=0.25)
            else:
                # bounded wait with small slices so we can be notified
                end = time.time() + float(timeout)
                while req.approved is None and time.time() < end:
                    req.condition.wait(timeout=0.25)

        if req.approved:
            print(f"[request_approval] woke: id={req.id} approved={req.approved} error={req.error}")

            return req.result
        return None

    def get_pending_requests(self) -> List[ApprovalRequest]:
        pend = [r for r in self._requests if r.approved is None]
        print(f"[get_pending] pending={len(pend)} total={len(self._requests)} queue_id={id(self)}")
        return pend

    def approve_request(self, request_id: int) -> Optional[object]:
        req = self._find_request(request_id)
        if req and req.approved is None:
            with req.condition:
                result = self._execute_request(req)
                req.condition.notify()
            return result
        return None

    def approve_batch(self, count: int):
        """Immediately executes up to `count` queued items (manual convenience)."""
        with self._lock:
            self._auto_approve_count = max(0, int(count))
        while not self._queue.empty() and count > 0:
            req = self._queue.get()
            if req.approved is None:
                self._execute_request(req)
                with req.condition:
                    req.condition.notify()
            count -= 1

    def approve_all_pending(self):
        self.approve_batch(len(self.get_pending_requests()))

    def deny_request(self, request_id: int) -> bool:
        req = self._find_request(request_id)
        if req and req.approved is None:
            req.approved = False
            with req.condition:
                req.condition.notify()
            return True
        return False

    # -------- internals ------------------------------------------------------

    def _enqueue(self, description: str, call_fn: Callable[[], Any]) -> ApprovalRequest:
        with self._lock:
            request = ApprovalRequest(
                id=self._next_id,
                description=description,
                call_fn=call_fn
            )
            self._next_id += 1
            self._requests.append(request)
            self._queue.put(request)
            print(f"[enqueue] ++ id={request.id} total={len(self._requests)} pending={len([r for r in self._requests if r.approved is None])}")

            return request

    def _execute_request(self, request: ApprovalRequest):
        print(f"[execute] -> id={request.id} approved={request.approved} (before) queue_id={id(self)}")

        try:
            request.result = request.call_fn()
            request.approved = True
        except BaseException as e:
            request.error = e
            request.approved = False
        print(f"[execute] <- id={request.id} approved={request.approved} error={request.error}")

        return request.result

    def _find_request(self, request_id: int) -> Optional[ApprovalRequest]:
        return next((r for r in self._requests if r.id == request_id), None)


# --- Hard singleton wiring (module-global) -----------------------------------
import sys as _sys

# Reuse existing instance if the module is re-imported (prevents duplicates)
if hasattr(_sys.modules[__name__], "_GLOBAL_APPROVAL_QUEUE"):
    approval_queue = getattr(_sys.modules[__name__], "_GLOBAL_APPROVAL_QUEUE")
else:
    approval_queue = ApprovalQueue()
    setattr(_sys.modules[__name__], "_GLOBAL_APPROVAL_QUEUE", approval_queue)

def request_approval(description: str, call_fn: Callable[[], Any], timeout: Optional[float] = None) -> Optional[object]:
    return approval_queue.request_approval(description, call_fn, timeout=timeout)

# === Ailys patch: module-level re-exports for GUI/use (START) ===

def get_pending_requests() -> List[ApprovalRequest]:
    """Return the list of pending ApprovalRequest objects."""
    return approval_queue.get_pending_requests()

def get_pending_requests_summary() -> List[dict]:
    """Lightweight dicts for GUI list rendering: id, description, created order."""
    items = []
    for r in approval_queue.get_pending_requests():
        items.append({
            "id": r.id,
            "description": r.description,
            "approved": r.approved,  # always None here by definition
        })
    return items

def approve_request(request_id: int) -> Optional[object]:
    """Approve a specific pending request by id and execute it."""
    return approval_queue.approve_request(request_id)

def deny_request(request_id: int) -> bool:
    """Deny a specific pending request by id (does not execute the call)."""
    return approval_queue.deny_request(request_id)

def approve_batch(count: int) -> None:
    """Approve/execute up to count pending requests (manual convenience)."""
    return approval_queue.approve_batch(count)

def approve_all_pending() -> None:
    """Approve/execute all pending requests."""
    return approval_queue.approve_all_pending()

# === Ailys patch: module-level re-exports for GUI/use (END) ===


# Optional: quick identity check for debugging
def _debug_id() -> str:
    return f"{__file__} | queue_id={id(approval_queue)} | mode={approval_queue.get_mode()}"

def _debug_counts() -> str:
    """Return sizes for quick checks from GUI/task."""
    try:
        return f"requests={len(approval_queue._requests)} pending={len([r for r in approval_queue._requests if r.approved is None])}"
    except Exception as e:
        return f"error={e!r}"

print(f"[approval_queue READY] queue_id={id(approval_queue)} mode={approval_queue.get_mode()}")

