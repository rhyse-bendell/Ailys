import sys
import os
from typing import Optional
from PySide6.QtGui import QCursor

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QTabWidget, QLabel, QHBoxLayout, QTextEdit, QComboBox, QProgressBar, QLineEdit,
    QMessageBox, QListWidget, QGroupBox
)

from PySide6.QtCore import Qt, QThread, Signal, QTimer


from tasks.literature_review import run as run_litreview
from tasks.lit_search_collect import run_dedupe_only

from core.batch import run_batch_litreview
from memory_loader import load_reviews_to_memory
from tasks.chat import ChatSession

import core.approval_queue as approvals
from core import artificial_cognition as ac
from dotenv import load_dotenv

load_dotenv()

mode = (os.getenv("AILYS_APPROVAL_MODE") or "manual").strip().lower()
approvals.approval_queue.set_mode(mode)

# Optional: prove we all see the same queue
#try:
#    print("GUI approval queue:", approvals._debug_id(), approvals._debug_counts())
#except Exception:
#    pass


class TaskRunnerThread(QThread):
    update_status = Signal(str)
    finished = Signal(bool, str)  # success: bool, message: str

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.update_status.emit("Task started...")
            result = self.task_func(*self.args, **self.kwargs)
            if isinstance(result, tuple) and len(result) == 2:
                success, message = result
            else:
                success, message = True, "Task completed successfully."
            self.update_status.emit(message)
            self.finished.emit(success, message)
        except Exception as e:
            error_msg = f"❌ Error during task: {e}"
            self.update_status.emit(error_msg)
            self.finished.emit(False, error_msg)


class PipelineRunnerThread(QThread):
    """Run a sequence of (fn, kwargs) steps on a background thread."""
    update_status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, steps):
        super().__init__()
        self.steps = steps

    def run(self):
        try:
            for i, (label, fn, kwargs) in enumerate(self.steps, start=1):
                self.update_status.emit(f"▶️ {i}/{len(self.steps)}: {label}...")
                ok, msg = fn(**kwargs)
                if not ok:
                    raise RuntimeError(msg)
                self.update_status.emit(f"✅ {label}: {msg}")
            self.finished.emit(True, "Full Knowledge Space pipeline completed.")
        except Exception as e:
            self.finished.emit(False, f"❌ Pipeline error: {e}")


class AilysGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ailys - Modular Assistant")
        self.resize(1200, 700)
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(700)
        main_layout.addWidget(self.tabs, 3)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setPlaceholderText("Ailys will report messages and updates here.")
        self.chat_log.setMinimumWidth(400)
        main_layout.addWidget(self.chat_log, 2)

        # ---- Right-side persistent Approvals pane (brain label + list + controls) ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(8)

        self.brain_label = QLabel(f"Brain: {ac.model_summary()}")
        self.brain_label.setStyleSheet("color: #666;")
        right_layout.addWidget(self.brain_label, 0, Qt.AlignTop)

        # ---- Global busy indicator (non-blocking) ----
        self.global_busy = QProgressBar()
        self.global_busy.setRange(0, 0)           # marquee
        self.global_busy.setVisible(False)
        right_layout.addWidget(self.global_busy)

        # ---- Global busy indicator (non-blocking) ----
        self.global_busy = QProgressBar()
        self.global_busy.setRange(0, 0)           # marquee
        self.global_busy.setTextVisible(True)      # show label text while busy
        self.global_busy.setVisible(False)
        right_layout.addWidget(self.global_busy)

        # Track how many concurrent tasks are running so we can keep the spinner on
        # even if one subtask ends while others are still going.
        self._busy_active_count = 0

        # List of pending approvals
        self.approvals_list = QListWidget()
        right_layout.addWidget(self.approvals_list, 1)

        # --- Approvals pane state for robust updates ---
        self._approvals_last_ids = []  # last known ordering of request IDs
        self._approvals_selected_id = None  # remember selection across refreshes
        self._last_pending_count = -1  # for notification dedupe

        # keep _approvals_selected_id in sync when user changes row
        self.approvals_list.currentRowChanged.connect(
            lambda _: (self._remember_selection(), self._update_overrides_panel_state())
        )

        # Info/status line
        self.approvals_info = QLabel("")
        self.approvals_info.setStyleSheet("color: #555;")
        right_layout.addWidget(self.approvals_info)
        # ---- Optional overrides for the selected approval ----
        overrides_box = QGroupBox("Overrides (optional)")
        ov_layout = QVBoxLayout(overrides_box)

        self.override_model = QLineEdit()
        self.override_model.setPlaceholderText("Model (e.g., gpt-4o, gpt-5)")

        self.override_max_tokens = QLineEdit()
        self.override_max_tokens.setPlaceholderText("Max tokens (integer)")

        self.override_timeout = QLineEdit()
        self.override_timeout.setPlaceholderText("Timeout (seconds, e.g., 60)")

        ov_layout.addWidget(QLabel("Model:"))
        ov_layout.addWidget(self.override_model)
        ov_layout.addWidget(QLabel("Max Tokens:"))
        ov_layout.addWidget(self.override_max_tokens)
        ov_layout.addWidget(QLabel("Timeout (seconds):"))
        ov_layout.addWidget(self.override_timeout)

        # Show cost/flags (e.g., token-free requests)
        self.overrides_cost_label = QLabel("")
        self.overrides_cost_label.setStyleSheet("color: #2b6; font-style: italic;")
        ov_layout.addWidget(self.overrides_cost_label)


        right_layout.addWidget(overrides_box)

        # Controls row
        btn_row = QHBoxLayout()
        self.btn_approve_selected = QPushButton("Approve Selected")
        self.btn_deny_selected = QPushButton("Deny Selected")
        self.btn_refresh_approvals = QPushButton("Refresh")
        btn_row.addWidget(self.btn_approve_selected)
        btn_row.addWidget(self.btn_deny_selected)
        btn_row.addWidget(self.btn_refresh_approvals)
        right_layout.addLayout(btn_row)

        # Stop control row
        stop_row = QHBoxLayout()
        self.btn_stop_task = QPushButton("Stop Current Task")
        self.btn_stop_task.setToolTip("Sends a soft STOP signal (env + STOP file if available). The task will checkpoint and finalize.")
        stop_row.addWidget(self.btn_stop_task)
        right_layout.addLayout(stop_row)


        # Wire actions to handlers (defined below)
        self.btn_refresh_approvals.clicked.connect(self.refresh_approvals_pane)
        self.btn_approve_selected.clicked.connect(self.approve_selected_request)
        self.btn_deny_selected.clicked.connect(self.deny_selected_request)

        self.btn_stop_task.clicked.connect(self.stop_current_task)

        # Add to the main layout with smaller stretch
        main_layout.addWidget(right_panel, 1)

        # --- Tabs ---
        self.create_main_tab()
        self.create_api_config_tab()

        self.create_lit_search_tab()
        self.create_lit_relevance_tab()  # renamed inside to "Lit Rank/Pull"

        self.create_literature_tab()  # now includes Batch controls
        # self.create_batch_tab()         # merged into Literature Review tab

        self.create_chat_tab()

        self.create_knowledge_space_tab()
        self.create_ks_quickrun_tab()

        self.create_memory_tab()


        self.approval_timer = QTimer()
        self.approval_timer.timeout.connect(self.check_approval_notifications)
        self.approval_timer.start(5000)  # every 5 seconds
        QTimer.singleShot(200, self.check_approval_notifications)  # kick a first poll
        self.refresh_approvals_pane()

    # ---------- Global busy guard ----------
    def _busy_start(self, msg: str = "Working..."):
        # increment active task count
        try:
            self._busy_active_count += 1
        except Exception:
            self._busy_active_count = 1
        try:
            self.global_busy.setFormat(msg)
            self.global_busy.setVisible(True)
        except Exception:
            pass
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        except Exception:
            pass
        # optionally disable main tabs to avoid accidental clicks
        try:
            self.tabs.setEnabled(False)
        except Exception:
            pass

    def _busy_stop(self):
        # decrement active task count, but don't hide if approvals are pending
        try:
            self._busy_active_count = max(0, int(self._busy_active_count) - 1)
        except Exception:
            self._busy_active_count = 0

        # If any tasks still running, keep spinner with last label
        if self._busy_active_count > 0:
            return

        # No active tasks; if approvals pending, keep spinner on with an approvals label
        try:
            pending = approvals.approval_queue.get_pending_requests()
            if pending:
                self.global_busy.setFormat(f"Waiting for approvals… ({len(pending)})")
                self.global_busy.setVisible(True)
                # Do not re-enable tabs/cursor here; user is interacting anyway
                return
        except Exception:
            pass

        # Fully idle → hide spinner and restore UI
        try:
            self.global_busy.setVisible(False)
        except Exception:
            pass
        try:
            QApplication.restoreOverrideCursor()
        except Exception:
            pass
        try:
            self.tabs.setEnabled(True)
        except Exception:
            pass

    def _attach_busy(self, thread: QThread, label: str):
        """Attach spinner lifecycle to any QThread with a human-readable label."""
        try:
            thread.started.connect(lambda: self._busy_start(label))
            # QThread.finished emits (no args); our TaskRunnerThread.finished emits (bool,str).
            # Connect both safely:
            try:
                thread.finished.connect(lambda *_: self._busy_stop())
            except Exception:
                pass
        except Exception:
            pass

    def _maybe_busy_for_approvals(self):
        """Keep spinner visible when approvals are pending, even if no task thread is running."""
        try:
            pending = approvals.approval_queue.get_pending_requests()
            if pending and self._busy_active_count == 0:
                self.global_busy.setFormat(f"Waiting for approvals… ({len(pending)})")
                self.global_busy.setVisible(True)
            elif not pending and self._busy_active_count == 0:
                self.global_busy.setVisible(False)
        except Exception:
            pass


    # ----------------- Common helpers -----------------

    # ---- Approvals pane helpers -------------------------------------------------
    def _remember_selection(self):
        rid = self._selected_request_id()
        if rid is not None:
            self._approvals_selected_id = rid

    def _selected_request_id(self) -> Optional[int]:
        item = self.approvals_list.currentItem()
        if not item:
            return None
        text = item.text().strip()
        # Format created in refresh: "[id] description"
        try:
            if text.startswith("[") and "]" in text:
                return int(text[1:text.index("]")])
        except Exception:
            pass
        return None

    def _update_overrides_panel_state(self):
        """
        If the selected approval describes a token-free (network-only) task,
        disable model/token overrides and show a cost hint.
        We detect this via the description text containing 'NO LLM TOKENS'.
        """
        try:
            item = self.approvals_list.currentItem()
            text = item.text() if item else ""
            is_network_only = ("NO LLM TOKENS" in text) if text else False
            self.override_model.setEnabled(not is_network_only)
            self.override_max_tokens.setEnabled(not is_network_only)
            # Timeout is still relevant for network calls
            self.override_timeout.setEnabled(True)
            self.overrides_cost_label.setText("Cost: 0 tokens (network-only)" if is_network_only else "")
        except Exception:
            # Fail open
            self.override_model.setEnabled(True)
            self.override_max_tokens.setEnabled(True)
            self.override_timeout.setEnabled(True)
            self.overrides_cost_label.setText("")


    def refresh_approvals_pane(self):
        try:
            pending = approvals.get_pending_requests() if hasattr(approvals, "get_pending_requests") \
                else approvals.approval_queue.get_pending_requests()
        except Exception:
            pending = approvals.approval_queue.get_pending_requests()

        # compute new id list
        new_ids = [r.id for r in pending]

        # update info line (always)
        n = len(pending)
        self.approvals_info.setText(f"Pending approvals: {n}" if n else "No pending approvals.")

        # if content didn't change, don't repaint; preserves selection automatically
        if new_ids == self._approvals_last_ids:
            self._update_overrides_panel_state()
            return

        # remember selection (id) before rebuild
        self._remember_selection()

        # rebuild only when changed
        self.approvals_list.setUpdatesEnabled(False)
        try:
            self.approvals_list.clear()
            for r in pending:
                self.approvals_list.addItem(f"[{r.id}] {r.description}")

            # restore selection if still present
            if self._approvals_selected_id is not None:
                target = f"[{self._approvals_selected_id}] "
                for i in range(self.approvals_list.count()):
                    if self.approvals_list.item(i).text().startswith(target):
                        self.approvals_list.setCurrentRow(i)
                        break
        finally:
            self.approvals_list.setUpdatesEnabled(True)

        self._approvals_last_ids = new_ids
        self._update_overrides_panel_state()

    def approve_selected_request(self):
        rid = self._selected_request_id()
        if rid is None:
            self.approvals_info.setText("Select a request to approve.")
            return
        try:
            # Build overrides dict from the UI (only include valid entries)
            overrides = {}
            m = self.override_model.text().strip()
            if m:
                overrides["model"] = m
            t = self.override_max_tokens.text().strip()
            if t:
                try:
                    overrides["max_tokens"] = int(t)
                except ValueError:
                    self.chat_log.append("⚠️ Max Tokens must be an integer; ignoring override.")
            to = self.override_timeout.text().strip()
            if to:
                try:
                    overrides["timeout"] = float(to)
                except ValueError:
                    self.chat_log.append("⚠️ Timeout must be a number (seconds); ignoring override.")

            # IMPORTANT: Do NOT disable the buttons here; nested approvals may appear immediately.
            # Run approve on a background thread and keep the UI interactive.
            def _do_approve():
                if hasattr(approvals, "approve_request"):
                    approvals.approve_request(rid, overrides or None)
                else:
                    approvals.approval_queue.approve_request(rid, overrides or None)
                return True, f"Approved request {rid}"

            self._approve_thread = TaskRunnerThread(_do_approve)
            self._approve_thread.update_status.connect(self.chat_log.append)
            self._attach_busy(self._approve_thread, "Approving request…")

            def _done(ok, msg):
                # Do not toggle button enabled states; simply refresh list + show status.
                if ok:
                    self.chat_log.append(f"✅ {msg}.")
                else:
                    self.chat_log.append(f"❌ Approve error: {msg}")
                self.refresh_approvals_pane()

            self._approve_thread.finished.connect(_done)
            self._approve_thread.start()
            # Give immediate feedback and also refresh list so new child approvals show up.
            self.chat_log.append(f"⏩ Approval dispatched for [{rid}]. You may approve subsequent requests now.")
            self.refresh_approvals_pane()

        except Exception as e:
            self.chat_log.append(f"❌ Approve error: {e}")
            self.refresh_approvals_pane()

    def deny_selected_request(self):
        rid = self._selected_request_id()
        if rid is None:
            self.approvals_info.setText("Select a request to deny.")
            return
        try:
            # Keep UI interactive; do NOT disable buttons.
            def _do_deny():
                ok = approvals.deny_request(rid) if hasattr(approvals, "deny_request") \
                    else approvals.approval_queue.deny_request(rid)
                if ok is False:
                    return False, "Could not deny request (maybe already resolved)."
                return True, f"Denied request {rid}"

            self._deny_thread = TaskRunnerThread(_do_deny)
            self._deny_thread.update_status.connect(self.chat_log.append)
            self._attach_busy(self._deny_thread, "Denying request…")

            def _done(ok, msg):
                self.chat_log.append(("✅ " if ok else "⚠️ ") + msg)
                self.refresh_approvals_pane()

            self._deny_thread.finished.connect(_done)
            self._deny_thread.start()
            # Immediate refresh so the list reflects the action quickly.
            self.refresh_approvals_pane()

        except Exception as e:
            self.chat_log.append(f"❌ Deny error: {e}")
            self.refresh_approvals_pane()

    def stop_current_task(self):
        """
        Sends a cooperative stop signal to running tasks that honor:
          - env var LIT_STOP=1
          - STOP file at path given by env var LIT_STOP_FLAG_PATH
        """
        try:
            os.environ["LIT_STOP"] = "1"
            stop_hint = os.environ.get("LIT_STOP_FLAG_PATH", "").strip()
            made_file = False
            if stop_hint:
                try:
                    # Ensure parent dir then create/touch the STOP file
                    os.makedirs(os.path.dirname(stop_hint) or ".", exist_ok=True)
                    with open(stop_hint, "a", encoding="utf-8") as f:
                        f.write("STOP\n")
                    made_file = True
                except Exception as e:
                    self.chat_log.append(f"⚠️ Could not create STOP file at {stop_hint}: {e}")
            msg = "🛑 Stop signal sent (env)."
            if made_file:
                msg += f" STOP file touched at: {stop_hint}"
            self.chat_log.append(msg)
        except Exception as e:
            self.chat_log.append(f"❌ Stop failed: {e}")


    def check_approval_notifications(self):
        pending = approvals.approval_queue.get_pending_requests()
        count = len(pending)
        #print(f"[GUI timer] queue_id={id(approvals.approval_queue)} pending={count}")

        # only log when the number changes
        if count != self._last_pending_count:
            if count > 0:
                self.chat_log.append(f"⚠️ {count} approval request(s) pending.")
                try:
                    self.chat_display.append(
                        f"⚠️ Ailys: You have {count} API request(s) waiting in the Approvals pane."
                    )
                except Exception:
                    pass
            self._last_pending_count = count


        # update list using the selection-preserving refresh
        self.refresh_approvals_pane()
        # Keep the spinner reflecting approvals-only idle state
        self._maybe_busy_for_approvals()


    def ask_ks_mode(self, title: str = "Select source mode"):
        """
        Show a 3-button dialog: Use Change Logs / Use Local Edits / Cancel.
        Returns:
            True  => downloaded/log_only (use change logs)
            False => local/auto      (use local filesystem diffs)
            None  => user canceled
        """
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText("How should Ailys infer the timeline for this run?")
        logs_btn = box.addButton("Use change logs", QMessageBox.AcceptRole)
        local_btn = box.addButton("Use local edits", QMessageBox.DestructiveRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(logs_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked == cancel_btn:
            self.chat_log.append("↩️ Canceled by user.")
            return None
        if clicked == logs_btn:
            return True
        return False

    # ----------------- Tabs -----------------

    def create_main_tab(self):
        main_tab = QWidget()
        layout = QVBoxLayout(main_tab)
        layout.addWidget(QLabel("Welcome to Ailys. Select a task tab above to get started."))
        self.tabs.addTab(main_tab, "Main")

    def create_api_config_tab(self):
        """
        API & Keys configuration tab.
        - Auto-loads ..env into masked fields
        - Lets you edit values (emails visible, keys masked)
        - Saves back to ..env and updates os.environ for this session
        - Leaving fields empty is OK (app runs in 'no-key' mode)
        """
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QLabel, QLineEdit,
            QPushButton, QHBoxLayout, QMessageBox
        )
        from core.config import load_env, save_env_updates

        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(
            QLabel("These settings are optional. If left blank, Ailys will operate in a slower, no-key mode."))

        # --- Fields (keep references on self for handlers) -----------------------
        self.cfg_openai = QLineEdit();
        self.cfg_openai.setEchoMode(QLineEdit.Password)
        self.cfg_openalex = QLineEdit()
        self.cfg_crossref = QLineEdit()
        self.cfg_s2 = QLineEdit();
        self.cfg_s2.setEchoMode(QLineEdit.Password)
        self.cfg_ncbi = QLineEdit();
        self.cfg_ncbi.setEchoMode(QLineEdit.Password)
        self.cfg_rate = QLineEdit()
        self.cfg_mode = QLineEdit()
        self.cfg_provider = QLineEdit()  # "openai" | "openai_compatible"
        self.cfg_model = QLineEdit()  # e.g., "gpt-4o", "gpt-5"
        self.cfg_base_url = QLineEdit()  # e.g., "http://localhost:11434/v1" for local servers

        def add_row(label_text, widget):
            layout.addWidget(QLabel(label_text))
            layout.addWidget(widget)

        add_row("OpenAI API Key", self.cfg_openai)
        add_row("OpenAlex email (mailto)", self.cfg_openalex)
        add_row("Crossref email (mailto)", self.cfg_crossref)
        add_row("Semantic Scholar API Key", self.cfg_s2)
        add_row("NCBI (PubMed) API Key", self.cfg_ncbi)
        add_row("Polite throttle seconds (LIT_RATE_LIMIT_SEC)", self.cfg_rate)
        add_row("Approval mode (manual | auto | dryrun) [AILYS_APPROVAL_MODE]", self.cfg_mode)
        add_row("LLM Provider (AILYS_PROVIDER: openai | openai_compatible)", self.cfg_provider)
        add_row("LLM Model (AILYS_MODEL)", self.cfg_model)
        add_row("LLM Base URL (AILYS_BASE_URL; for compatible servers)", self.cfg_base_url)

        # Buttons row
        btns = QHBoxLayout()
        self.btn_cfg_reload = QPushButton("Reload from ..env")
        self.btn_cfg_save = QPushButton("Save")
        self.btn_cfg_toggle = QPushButton("Show/Hide Secrets")
        btns.addWidget(self.btn_cfg_reload)
        btns.addWidget(self.btn_cfg_save)
        btns.addWidget(self.btn_cfg_toggle)
        layout.addLayout(btns)

        # Wire handlers
        from dotenv import dotenv_values, find_dotenv
        self.env_path = find_dotenv(usecwd=True) or "..env"

        def _merged_env():
            """Merge ..env and process environment variables."""
            file_vals = dotenv_values(self.env_path) or {}
            merged = dict(os.environ)
            merged.update({k: v for k, v in file_vals.items() if v is not None})
            return merged

        def reload_fields():
            vals = _merged_env()
            self.cfg_openai.setText(vals.get("OPENAI_API_KEY", ""))
            self.cfg_openalex.setText(vals.get("OPENALEX_EMAIL", ""))  # ensure key matches your ..env
            self.cfg_crossref.setText(vals.get("CROSSREF_MAILTO", ""))
            self.cfg_s2.setText(vals.get("SEMANTIC_SCHOLAR_KEY", ""))
            self.cfg_ncbi.setText(vals.get("NCBI_API_KEY", ""))
            self.cfg_rate.setText(vals.get("LIT_RATE_LIMIT_SEC", "1.5"))
            self.cfg_mode.setText(vals.get("AILYS_APPROVAL_MODE", "manual"))
            self.cfg_provider.setText(vals.get("AILYS_PROVIDER", "openai"))
            self.cfg_model.setText(vals.get("AILYS_MODEL", "gpt-4o"))
            self.cfg_base_url.setText(vals.get("AILYS_BASE_URL", ""))

            # Optional feedback to chat log
            try:
                self.parent().chat_log.append(f"Loaded config from: {self.env_path}")
            except Exception:
                pass

        def save_fields():
            updates = {
                "OPENAI_API_KEY": self.cfg_openai.text().strip(),
                "OPENALEX_EMAIL": self.cfg_openalex.text().strip(),
                "CROSSREF_MAILTO": self.cfg_crossref.text().strip(),
                "SEMANTIC_SCHOLAR_KEY": self.cfg_s2.text().strip(),
                "NCBI_API_KEY": self.cfg_ncbi.text().strip(),
                "LIT_RATE_LIMIT_SEC": self.cfg_rate.text().strip(),
                "AILYS_APPROVAL_MODE": self.cfg_mode.text().strip(),
                "AILYS_PROVIDER": self.cfg_provider.text().strip(),
                "AILYS_MODEL": self.cfg_model.text().strip(),
                "AILYS_BASE_URL": self.cfg_base_url.text().strip()
            }
            try:
                from core.config import save_env_updates
                save_env_updates(updates, self.env_path)
                # Apply to current process so artificial_cognition reads the new values right away
                for k, v in updates.items():
                    if v is not None:  # empty strings are okay; they clear a value
                        os.environ[k] = v

                # If approval mode changed, apply it to the shared queue
                try:
                    approvals.approval_queue.set_mode(self.cfg_mode.text().strip().lower())
                except Exception:
                    pass

                # Refresh the visible brain summary label
                try:
                    self.parent().chat_log.append("Updated LLM provider/model configuration.")
                except Exception:
                    pass
                self.brain_label.setText(f"Brain: {ac.model_summary()}")

                QMessageBox.information(
                    self,
                    "Saved",
                    f"Configuration saved to {self.env_path} and applied to this session."
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save ..env: {e}")

        def toggle_secrets():
            # flip echo mode for secret fields
            for w in (self.cfg_openai, self.cfg_s2, self.cfg_ncbi):
                w.setEchoMode(
                    QLineEdit.Normal if w.echoMode() == QLineEdit.Password else QLineEdit.Password
                )

        self.btn_cfg_reload.clicked.connect(reload_fields)
        self.btn_cfg_save.clicked.connect(save_fields)
        self.btn_cfg_toggle.clicked.connect(toggle_secrets)

        # Initial populate from ..env
        reload_fields()

        self.tabs.addTab(tab, "Config")

    # (Optional) If you prefer separate named handlers, you can break the inner functions out:
    # def reload_api_config(self): ...
    # def save_api_config(self): ...
    # def toggle_api_secrets(self): ...

    def create_lit_search_tab(self):
        """Creates the Literature Search tab with Stage A–B functionality (flow-ordered)."""

        from PySide6.QtWidgets import (
            QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
            QTabWidget, QLabel, QHBoxLayout, QTextEdit, QComboBox, QProgressBar, QLineEdit,
            QMessageBox, QListWidget, QGroupBox
        )

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 1) Researcher name ---------------------------------------------------------
        researcherBox = QGroupBox("Researcher")
        rLay = QHBoxLayout(researcherBox)
        self.ls_researcher = QLineEdit()
        self.ls_researcher.setPlaceholderText("Enter your display name (e.g., Ailys)")
        rLay.addWidget(QLabel("Name:"))
        rLay.addWidget(self.ls_researcher)
        layout.addWidget(researcherBox)

        # 2) Search prompt -> generate keywords CSV ---------------------------------
        genBox = QGroupBox("Search Prompt → Generate Keywords (CSV-1)")
        gLay = QVBoxLayout(genBox)
        self.ls_prompt = QTextEdit()
        self.ls_prompt.setPlaceholderText(
            "Describe your literature search goal...\n"
            "Example: I need to find literature on neurodiversity in teams, "
            "especially where AI supports collaboration or task performance."
        )

        self.btn_ls_keywords = QPushButton("Generate Keywords (CSV-1)")
        gLay.addWidget(QLabel("Prompt:"))
        gLay.addWidget(self.ls_prompt)

        # NEW: Save prefix for CSV-1 outputs
        kpRow = QHBoxLayout()
        self.ls_keywords_prefix = QLineEdit()
        self.ls_keywords_prefix.setPlaceholderText("Optional save prefix for CSV-1 (e.g., collabLearning)")
        kpRow.addWidget(QLabel("Save prefix:"))
        kpRow.addWidget(self.ls_keywords_prefix)
        gLay.addLayout(kpRow)

        gLay.addWidget(self.btn_ls_keywords)



        layout.addWidget(genBox)

        # 3) Augment an existing keywords CSV with a new clarification ---------------
        augBox = QGroupBox("Augment Existing Keywords CSV")
        aLay = QVBoxLayout(augBox)

        # File picker row
        fRow = QHBoxLayout()
        self.ls_aug_csv_path = QLineEdit()
        self.ls_aug_csv_path.setPlaceholderText("Path to existing prompt_to_keywords.csv")
        btn_browse_aug = QPushButton("Browse…")
        fRow.addWidget(QLabel("Existing CSV:"))
        fRow.addWidget(self.ls_aug_csv_path)
        fRow.addWidget(btn_browse_aug)
        aLay.addLayout(fRow)

        # Clarification text
        self.ls_aug_text = QTextEdit()
        self.ls_aug_text.setPlaceholderText(
            "Add clarification or updates to refine/amend the existing keywords and queries."
        )
        aLay.addWidget(QLabel("Additional Clarification / Update:"))
        aLay.addWidget(self.ls_aug_text)

        self.btn_ls_augment = QPushButton("Augment Keywords CSV")
        aLay.addWidget(self.btn_ls_augment)
        layout.addWidget(augBox)

        # 4) Manuscript collection using a chosen keywords CSV -----------------------
        colBox = QGroupBox("Collect Candidate Records (Guided by Keywords CSV)")
        cLay = QVBoxLayout(colBox)

        cRow = QHBoxLayout()
        self.ls_csv1_path = QLineEdit()
        self.ls_csv1_path.setPlaceholderText("Path to keywords CSV to use for collection")
        btn_browse_csv1 = QPushButton("Browse…")
        cRow.addWidget(QLabel("Keywords CSV:"))
        cRow.addWidget(self.ls_csv1_path)
        cRow.addWidget(btn_browse_csv1)
        cLay.addLayout(cRow)

        # NEW: Save prefix for CSV-2 collection outputs
        cpRow = QHBoxLayout()
        self.ls_collect_prefix = QLineEdit()
        self.ls_collect_prefix.setPlaceholderText("Optional save prefix for collection (e.g., collabLearning)")
        cpRow.addWidget(QLabel("Save prefix:"))
        cpRow.addWidget(self.ls_collect_prefix)
        cLay.addLayout(cpRow)

        self.btn_ls_collect = QPushButton("Request Approval & Start Collection (NO LLM TOKENS)")
        cLay.addWidget(self.btn_ls_collect)
        layout.addWidget(colBox)

        # Browse handlers
        def browse_aug_csv():
            path, _ = QFileDialog.getOpenFileName(self, "Select prompt_to_keywords.csv", "", "CSV Files (*.csv)")
            if path:
                self.ls_aug_csv_path.setText(path)

        def browse_csv1():
            path, _ = QFileDialog.getOpenFileName(self, "Select keywords CSV for collection", "", "CSV Files (*.csv)")
            if path:
                self.ls_csv1_path.setText(path)

        btn_browse_aug.clicked.connect(browse_aug_csv)
        btn_browse_csv1.clicked.connect(browse_csv1)

        # Wire actions
        self.btn_ls_keywords.clicked.connect(self.run_ls_keywords)
        self.btn_ls_augment.clicked.connect(self.run_ls_augment)
        self.btn_ls_collect.clicked.connect(self.run_ls_collect)

        # Add Tab
        self.tabs.addTab(tab, "Lit Search")

    # =========================================================================== #
    # -------------------------- Button Handlers -------------------------------- #
    # =========================================================================== #
    # -------------------------- Lit Relevance Tab ------------------------------ #
    def create_lit_relevance_tab(self):
        """
        Stage C – Relevance scoring (CSV-2 → rank-ordered CSV for PDF pulls).
        Also: De-dup-only helper and Zero-LLM Triage splitter.
        """
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
            QPushButton, QFileDialog, QGroupBox
        )
        import shutil
        import re

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ------------------- De-dup-only UI -------------------
        dedupe_box = QGroupBox("De-duplicate an Existing CSV → FINAL")
        d_lay = QVBoxLayout(dedupe_box)

        # Input CSV
        drow1 = QHBoxLayout()
        self.dedupe_input_csv = QLineEdit()
        self.dedupe_input_csv.setPlaceholderText("Path to large CSV (e.g., checkpoint/raw/combined)")
        btn_browse_dedupe_in = QPushButton("Browse…")
        drow1.addWidget(QLabel("Input CSV:"))
        drow1.addWidget(self.dedupe_input_csv)
        drow1.addWidget(btn_browse_dedupe_in)
        d_lay.addLayout(drow1)

        # Output folder + Save prefix
        drow2 = QHBoxLayout()
        self.dedupe_output_dir = QLineEdit()
        self.dedupe_output_dir.setPlaceholderText("Optional: output folder (default = same folder as input)")
        btn_browse_dedupe_out = QPushButton("Choose…")
        drow2.addWidget(QLabel("Output Folder:"))
        drow2.addWidget(self.dedupe_output_dir)
        drow2.addWidget(btn_browse_dedupe_out)
        d_lay.addLayout(drow2)

        drow3 = QHBoxLayout()
        self.dedupe_prefix = QLineEdit()
        self.dedupe_prefix.setPlaceholderText("Optional save prefix (e.g., collabLearning)")
        drow3.addWidget(QLabel("Save prefix:"))
        drow3.addWidget(self.dedupe_prefix)
        d_lay.addLayout(drow3)

        self.btn_run_dedupe_only = QPushButton("Run De-duplication (NO LLM TOKENS)")
        d_lay.addWidget(self.btn_run_dedupe_only)

        # Note about scale
        d_lay.addWidget(QLabel(
            "Note: handles very large CSVs, but RAM usage will scale with rows. "
            "Default filename is 'search_results_final.csv'; if a prefix is provided, "
            "output is placed in a prefix-named subfolder and renamed to '<prefix>_search_results_final.csv'."
        ))

        layout.addWidget(dedupe_box)

        # ------------------- Zero-LLM Triage UI -------------------
        tri_box = QGroupBox("Triage Candidates (Zero-LLM) → Ready vs Requires Amendment")
        t_lay = QVBoxLayout(tri_box)

        trow1 = QHBoxLayout()
        self.triage_input_csv = QLineEdit()
        self.triage_input_csv.setPlaceholderText("Path to search_results_final.csv")
        btn_browse_tri_in = QPushButton("Browse…")
        trow1.addWidget(QLabel("Candidates CSV:"))
        trow1.addWidget(self.triage_input_csv)
        trow1.addWidget(btn_browse_tri_in)
        t_lay.addLayout(trow1)

        trow2 = QHBoxLayout()
        self.triage_prefix = QLineEdit()
        self.triage_prefix.setPlaceholderText("Save prefix (e.g., collabLearning)")
        trow2.addWidget(QLabel("Save prefix:"))
        trow2.addWidget(self.triage_prefix)
        t_lay.addLayout(trow2)

        self.btn_run_triage = QPushButton("Run Triage (No LLM; cleans mojibake; splits files)")
        t_lay.addWidget(self.btn_run_triage)

        layout.addWidget(tri_box)

        # ------------------- Relevance UI -------------------
        ibox = QGroupBox("Rank / Relevance (CSV-2 → Ranked)")
        ilay = QVBoxLayout(ibox)

        # CSV-1 (prompt_to_keywords.csv)
        row1 = QHBoxLayout()
        self.rel_csv1_path = QLineEdit()
        self.rel_csv1_path.setPlaceholderText("Path to prompt_to_keywords.csv")
        btn_browse_csv1 = QPushButton("Browse…")
        row1.addWidget(QLabel("Keywords CSV (CSV-1):"))
        row1.addWidget(self.rel_csv1_path)
        row1.addWidget(btn_browse_csv1)
        ilay.addLayout(row1)

        # Collected CSV (optional)
        row2 = QHBoxLayout()
        self.rel_input_csv = QLineEdit()
        self.rel_input_csv.setPlaceholderText("Path to search_results_final.csv")
        btn_browse_input = QPushButton("Browse…")
        row2.addWidget(QLabel("Collected CSV (CSV-2):"))
        row2.addWidget(self.rel_input_csv)
        row2.addWidget(btn_browse_input)
        ilay.addLayout(row2)

        # Save prefix for relevance outputs (passed through when supported)
        row2b = QHBoxLayout()
        self.rel_save_prefix = QLineEdit()
        self.rel_save_prefix.setPlaceholderText("Save prefix for relevance outputs (e.g., collabLearning)")
        row2b.addWidget(QLabel("Save prefix:"))
        row2b.addWidget(self.rel_save_prefix)
        ilay.addLayout(row2b)

        # Batch size + Max items
        row3 = QHBoxLayout()
        self.rel_batch_size = QLineEdit()
        self.rel_batch_size.setPlaceholderText("e.g., 15")
        self.rel_max_items = QLineEdit()
        self.rel_max_items.setPlaceholderText("Optional cap, e.g., 200")
        row3.addWidget(QLabel("Batch size:"))
        row3.addWidget(self.rel_batch_size)
        row3.addWidget(QLabel("Max items:"))
        row3.addWidget(self.rel_max_items)
        ilay.addLayout(row3)

        # Optional literature need override
        self.rel_need_override = QTextEdit()
        self.rel_need_override.setPlaceholderText(
            "Optional: override the literature need / context for this scoring run.\n"
            "If left blank, the task will use details from CSV-1."
        )
        ilay.addWidget(QLabel("Override Literature Need (optional)"))
        ilay.addWidget(self.rel_need_override)

        layout.addWidget(ibox)

        # Actions (Relevance)
        self.btn_rel_run = QPushButton("Run Relevance Scoring")
        layout.addWidget(self.btn_rel_run)

        # ------------------- Pull PDFs UI -------------------
        pull_box = QGroupBox("Pull PDFs for Ranked/Edited CSV")
        p_lay = QVBoxLayout(pull_box)

        prow1 = QHBoxLayout()
        self.rel_ranked_csv = QLineEdit()
        self.rel_ranked_csv.setPlaceholderText("Path to ranked/edited CSV (output of relevance)")
        btn_browse_ranked = QPushButton("Browse…")
        prow1.addWidget(QLabel("Ranked CSV:"))
        prow1.addWidget(self.rel_ranked_csv)
        prow1.addWidget(btn_browse_ranked)
        p_lay.addLayout(prow1)

        prow2 = QHBoxLayout()
        self.rel_pull_max = QLineEdit()
        self.rel_pull_max.setPlaceholderText("Optional cap, e.g., 200")
        prow2.addWidget(QLabel("Max items:"))
        prow2.addWidget(self.rel_pull_max)
        p_lay.addLayout(prow2)

        self.btn_rel_pull = QPushButton("Pull PDFs for Ranked CSV")
        p_lay.addWidget(self.btn_rel_pull)

        layout.addWidget(pull_box)

        # ------------------- Browse handlers -------------------
        def browse_dedupe_in():
            path, _ = QFileDialog.getOpenFileName(self, "Select CSV to de-duplicate", "", "CSV Files (*.csv)")
            if path:
                self.dedupe_input_csv.setText(path)

        def browse_dedupe_out():
            path = QFileDialog.getExistingDirectory(self, "Choose output folder")
            if path:
                self.dedupe_output_dir.setText(path)

        def browse_triage_in():
            path, _ = QFileDialog.getOpenFileName(self, "Select search_results_final.csv", "", "CSV Files (*.csv)")
            if path:
                self.triage_input_csv.setText(path)

        def browse_csv1():
            path, _ = QFileDialog.getOpenFileName(self, "Select prompt_to_keywords.csv", "", "CSV Files (*.csv)")
            if path:
                self.rel_csv1_path.setText(path)

        def browse_input():
            path, _ = QFileDialog.getOpenFileName(self, "Select search_results_final.csv", "", "CSV Files (*.csv)")
            if path:
                self.rel_input_csv.setText(path)

        def browse_ranked():
            path, _ = QFileDialog.getOpenFileName(self, "Select ranked/edited CSV", "", "CSV Files (*.csv)")
            if path:
                self.rel_ranked_csv.setText(path)

        btn_browse_dedupe_in.clicked.connect(browse_dedupe_in)
        btn_browse_dedupe_out.clicked.connect(browse_dedupe_out)
        btn_browse_tri_in.clicked.connect(browse_triage_in)
        btn_browse_csv1.clicked.connect(browse_csv1)
        btn_browse_input.clicked.connect(browse_input)
        btn_browse_ranked.clicked.connect(browse_ranked)

        # ------------------- Run handlers -------------------
        def _run_dedupe_only():
            csv_path = self.dedupe_input_csv.text().strip()
            out_dir = self.dedupe_output_dir.text().strip()
            prefix = self.dedupe_prefix.text().strip()

            if not csv_path:
                self.chat_log.append("⚠️ Please select an input CSV to de-duplicate.")
                return

            # If prefix provided and no explicit out_dir, create a prefix-named subfolder next to the input.
            if prefix and not out_dir:
                base_dir = os.path.dirname(os.path.abspath(csv_path))
                out_dir = os.path.join(base_dir, prefix)

            self.chat_log.append("⏳ De-duplication started (NO LLM TOKENS).")

            def _task():
                try:
                    # Run task
                    ok, msg = run_dedupe_only(csv_path, out_dir or None)

                    # If prefix supplied, rename final file to include the prefix
                    if ok and prefix:
                        dest_dir = out_dir or os.path.dirname(os.path.abspath(csv_path))
                        try:
                            os.makedirs(dest_dir, exist_ok=True)
                        except Exception:
                            pass
                        final_default = os.path.join(dest_dir, "search_results_final.csv")
                        final_pref = os.path.join(dest_dir, f"{prefix}_search_results_final.csv")
                        try:
                            if os.path.exists(final_default):
                                # If a prefixed file already exists, overwrite it
                                try:
                                    if os.path.exists(final_pref):
                                        os.remove(final_pref)
                                except Exception:
                                    pass
                                os.replace(final_default, final_pref)
                                msg = re.sub(r"(FINAL .*written:\s*)(.+?)(\s*\| rows=)", r"\1" + final_pref + r"\3",
                                             msg)
                        except Exception as e:
                            msg += f"\n⚠️ Could not rename final CSV to prefixed name: {e}"

                    return ok, msg
                except Exception as e:
                    return False, f"De-duplication failed: {e}"

            self.thread = TaskRunnerThread(_task)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "Dedupe: Processing CSV…")
            self.thread.start()

        self.btn_run_dedupe_only.clicked.connect(_run_dedupe_only)

        def _run_triage():
            input_csv = self.triage_input_csv.text().strip()
            prefix = self.triage_prefix.text().strip() or "relevance"
            if not input_csv:
                self.chat_log.append("⚠️ Please select a candidates CSV (search_results_final.csv).")
                return

            self.chat_log.append(
                "⏳ Running triage (Zero-LLM). This will clean obvious mojibake and split into ready/needs-amendment…")

            def _task():
                try:
                    from tasks.lit_triage import run_triage
                except Exception as e:
                    return False, f"Could not import triage task: {e}"
                ok, msg = run_triage(input_csv=input_csv, save_prefix=prefix, write_md_preview=True)
                return ok, msg

            self.thread = TaskRunnerThread(_task)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "Triaging candidates…")
            self.thread.start()

        self.btn_run_triage.clicked.connect(_run_triage)

        def _run_rel():
            csv1 = self.rel_csv1_path.text().strip()
            if not csv1:
                self.chat_log.append("⚠️ Please select the CSV-1 (prompt_to_keywords.csv).")
                return

            input_csv = self.rel_input_csv.text().strip() or None
            save_prefix = (self.rel_save_prefix.text().strip() or None)

            batch = None
            btxt = self.rel_batch_size.text().strip()
            if btxt:
                try:
                    batch = int(btxt)
                except ValueError:
                    self.chat_log.append("⚠️ Batch size must be an integer; leaving default.")
                    batch = None

            max_items = None
            mtxt = self.rel_max_items.text().strip()
            if mtxt:
                try:
                    max_items = int(mtxt)
                except ValueError:
                    self.chat_log.append("⚠️ Max items must be an integer; ignoring.")
                    max_items = None

            need_override = self.rel_need_override.toPlainText().strip() or None

            self.chat_log.append("⏳ Relevance scoring will request approvals per batch in the Approvals pane.")

            def _task():
                try:
                    from tasks.lit_review_relevance import run as rel_run
                except Exception as e:
                    return False, f"Could not import relevance task: {e}"

                # Pass save_prefix if the task supports it; fall back gracefully otherwise.
                kwargs = dict(
                    csv1_path=csv1,
                    collected_csv_path=input_csv,
                    batch_size=batch,
                    max_items=max_items,
                    need_override=need_override
                )
                if save_prefix:
                    kwargs["save_prefix"] = save_prefix

                try:
                    ok, msg = rel_run(**kwargs)
                except TypeError as te:
                    # Retry without save_prefix if the backend doesn't accept it yet
                    if "save_prefix" in kwargs:
                        kwargs.pop("save_prefix", None)
                        ok, msg = rel_run(**kwargs)
                        msg = msg + "\nℹ️ Note: save_prefix not supported by relevance task; ignored."
                    else:
                        raise
                return ok, msg

            self.thread = TaskRunnerThread(_task)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "Running relevance checker")
            self.thread.start()

        def _run_pull():
            ranked_csv = self.rel_ranked_csv.text().strip()
            if not ranked_csv:
                self.chat_log.append("⚠️ Please select the ranked/edited CSV.")
                return

            max_items = None
            mtxt = self.rel_pull_max.text().strip()
            if mtxt:
                try:
                    max_items = int(mtxt)
                except ValueError:
                    self.chat_log.append("⚠️ Max items must be an integer; ignoring.")
                    max_items = None

            self.chat_log.append("⏳ Pulling PDFs (NO LLM TOKENS). Check the Approvals pane if prompted.")

            def _task():
                try:
                    from tasks.lit_search_pull import run as pull_run
                except Exception as e:
                    return False, f"Could not import lit_search_pull: {e}"
                ok, msg = pull_run(input_csv=ranked_csv, out_root=None, max_items=max_items)
                return ok, msg

            self.thread = TaskRunnerThread(_task)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "Pulling PDFs…")
            self.thread.start()

        self.btn_rel_run.clicked.connect(_run_rel)
        self.btn_rel_pull.clicked.connect(_run_pull)

        # Renamed tab:
        self.tabs.addTab(tab, "Lit Rank/Pull")

    def run_ls_keywords(self):
        """Stage A – Prompt → Keywords (CSV-1)."""
        self.chat_log.append(
            "⏳ Waiting for your approval: open the Approvals pane (right) to allow 'Generate Keywords'.")

        prompt = self.ls_prompt.toPlainText().strip()
        researcher = self.ls_researcher.text().strip() or "Researcher"
        save_prefix = (self.ls_keywords_prefix.text().strip() or None)

        if not prompt:
            self.chat_log.append("⚠️ Please enter a search prompt for CSV-1 generation.")
            return

        def _task():
            from tasks.lit_search_keywords import run as run_keywords
            kwargs = dict(
                root=None,
                guidance=prompt,
                clarifications_csv_path=None,  # no CSV in this stage after UI refactor
                researcher=researcher
            )
            if save_prefix:
                kwargs["save_prefix"] = save_prefix

            try:
                ok, msg = run_keywords(**kwargs)
            except TypeError:
                # Older task without save_prefix support — retry without it
                if "save_prefix" in kwargs:
                    kwargs.pop("save_prefix", None)
                    ok, msg = run_keywords(**kwargs)
                    msg = msg + "\nℹ️ Note: save_prefix not supported by Keywords task; ignored."
                else:
                    raise
            return ok, msg

        self.thread = TaskRunnerThread(_task)
        self.thread.update_status.connect(self.chat_log.append)
        self.thread.finished.connect(self.task_finished_with_result)
        self._attach_busy(self.thread, "Generating Keywords (CSV-1)…")
        self.thread.start()

    def run_ls_augment(self):
        """Augment an existing keywords CSV using a new clarification prompt."""
        existing_csv = self.ls_aug_csv_path.text().strip()
        clar = self.ls_aug_text.toPlainText().strip()
        researcher = self.ls_researcher.text().strip() or "Researcher"

        if not existing_csv:
            self.chat_log.append("⚠️ Please select the existing keywords CSV to augment.")
            return
        if not clar:
            self.chat_log.append("⚠️ Please enter a clarification/update to guide the augmentation.")
            return

        self.chat_log.append(
            "⏳ Waiting for your approval: use the Approvals pane (right side) to allow 'Augment Keywords'.")

        def _task():
            from tasks.lit_search_keywords import augment_keywords_csv
            out_path = existing_csv + ".updated.csv"
            ok_path = augment_keywords_csv(existing_csv, clar, out_path, researcher=researcher)
            return True, f"CSV written: {ok_path}"

        self.thread = TaskRunnerThread(_task)
        self.thread.update_status.connect(self.chat_log.append)
        self.thread.finished.connect(self.task_finished_with_result)
        self._attach_busy(self.thread, "Augmenting Keywords CSV…")
        self.thread.start()

    def run_ls_collect(self):
        """Stage B – Keywords → Candidate Records (CSV-2)."""
        csv1 = self.ls_csv1_path.text().strip()
        researcher = self.ls_researcher.text().strip() or None
        save_prefix = (self.ls_collect_prefix.text().strip() or None)

        if not csv1:
            self.chat_log.append("⚠️ Please select the CSV-1 file (prompt_to_keywords.csv).")
            return

        def _task():
            from tasks.lit_search_collect import run as run_collect
            kwargs = dict(csv1_path=csv1, researcher=researcher, per_source=20)
            if save_prefix:
                kwargs["save_prefix"] = save_prefix
            try:
                ok, msg = run_collect(**kwargs)
            except TypeError:
                # Older task without save_prefix support — retry without it
                if "save_prefix" in kwargs:
                    kwargs.pop("save_prefix", None)
                    ok, msg = run_collect(**kwargs)
                    msg = msg + "\nℹ️ Note: save_prefix not supported by Collection task; ignored."
                else:
                    raise
            return ok, msg

        self.thread = TaskRunnerThread(_task)
        self.thread.update_status.connect(self.chat_log.append)
        self.thread.finished.connect(self.task_finished_with_result)
        self._attach_busy(self.thread, "Collecting literature (CSV-2)…")
        self.thread.start()

    def open_ls_output_folder(self):
        """Open the last known Lit Search output folder in the system file explorer."""
        try:
            out_dir = getattr(self, "_ls_last_out_dir", None)
            if not out_dir or not os.path.isdir(out_dir):
                self.chat_log.append("ℹ️ No output folder available yet.")
                return
            # Windows
            try:
                os.startfile(out_dir)
                return
            except AttributeError:
                pass
            # macOS
            if sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", out_dir])
                return
            # Linux
            import subprocess
            subprocess.Popen(["xdg-open", out_dir])
        except Exception as e:
            self.chat_log.append(f"⚠️ Could not open folder: {e}")

    def create_literature_tab(self):
        lit_tab = QWidget()
        layout = QVBoxLayout(lit_tab)

        # -------- Single-file review controls --------
        self.guidance_input = QTextEdit()
        self.guidance_input.setPlaceholderText("Enter review guidance (optional)")
        layout.addWidget(self.guidance_input)

        file_button = QPushButton("Select PDF to Review")
        file_button.clicked.connect(self.select_pdf)
        layout.addWidget(file_button)

        output_file_button = QPushButton("Select Output Spreadsheet")
        output_file_button.clicked.connect(self.select_output_file)
        layout.addWidget(output_file_button)

        self.output_file_path = "outputs/C2_Lit_Review.xlsx"
        self.output_file_label = QLabel(f"Current Output: {self.output_file_path}")
        layout.addWidget(self.output_file_label)

        self.run_button = QPushButton("Run Literature Review")
        self.run_button.clicked.connect(self.run_literature_review)
        layout.addWidget(self.run_button)

        # Progress (shared for single + batch)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # -------- Batch review controls (merged here) --------
        batch_box = QGroupBox("Batch Review")
        b_layout = QVBoxLayout(batch_box)

        self.batch_folder_button = QPushButton("Select Folder for Batch Review")
        self.batch_folder_button.clicked.connect(self.select_batch_folder)
        b_layout.addWidget(self.batch_folder_button)

        self.batch_run_button = QPushButton("Run Batch Review")
        self.batch_run_button.clicked.connect(self.run_batch_review)
        b_layout.addWidget(self.batch_run_button)

        layout.addWidget(batch_box)

        self.tabs.addTab(lit_tab, "Literature Review")

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Select Output Spreadsheet", "", "Excel Files (*.xlsx)")
        if file_path:
            self.output_file_path = file_path
            self.output_file_label.setText(f"Current Output: {file_path}")
            self.chat_log.append(f"Output file set to: {file_path}")

    def create_batch_tab(self):
        batch_tab = QWidget()
        layout = QVBoxLayout(batch_tab)

        self.batch_folder_button = QPushButton("Select Folder for Batch Review")
        self.batch_folder_button.clicked.connect(self.select_batch_folder)
        layout.addWidget(self.batch_folder_button)

        self.batch_run_button = QPushButton("Run Batch Review")
        self.batch_run_button.clicked.connect(self.run_batch_review)
        layout.addWidget(self.batch_run_button)

        self.tabs.addTab(batch_tab, "Batch Review")

    def create_memory_tab(self):
        memory_tab = QWidget()
        layout = QVBoxLayout(memory_tab)

        self.recall_input = QLineEdit()
        self.recall_input.setPlaceholderText("Set recall depth (e.g., 13) or leave blank for default")
        layout.addWidget(QLabel("Optional Manual Recall Depth"))
        layout.addWidget(self.recall_input)

        self.recall_toggle = QComboBox()
        self.recall_toggle.addItems(["Low Recall Depth", "Medium Recall Depth", "High Recall Depth"])
        layout.addWidget(QLabel("Select Memory Recall Depth"))
        layout.addWidget(self.recall_toggle)

        memory_button = QPushButton("Import Review Memory")
        memory_button.clicked.connect(self.import_review_memory)
        layout.addWidget(memory_button)

        self.tabs.addTab(memory_tab, "Memory")


    def create_knowledge_space_tab(self):
        """Main KS controls (the existing 'list')."""
        ks_tab = QWidget()
        layout = QVBoxLayout(ks_tab)

        # Folder picker (shared by this tab)
        self.ks_folder_button = QPushButton("Select Knowledge Space Folder")
        self.ks_folder_button.clicked.connect(self.select_ks_folder)
        layout.addWidget(self.ks_folder_button)
        self.ks_folder_label = QLabel("No folder selected.")
        layout.addWidget(self.ks_folder_label)

        # Review
        self.ks_review_btn = QPushButton("Run Knowledge Space Review")
        self.ks_review_btn.clicked.connect(self.ks_run_review)
        layout.addWidget(self.ks_review_btn)

        # Timeline (JSON) – optional if you have a separate task; exports already carry timelines
        self.ks_timeline_btn = QPushButton("Generate Timeline (JSON)")
        self.ks_timeline_btn.clicked.connect(self.ks_generate_timeline)
        layout.addWidget(self.ks_timeline_btn)

        # Visualizations
        self.ks_viz_btn = QPushButton("Generate Timeline Visualizations")
        self.ks_viz_btn.clicked.connect(self.ks_generate_visuals)
        layout.addWidget(self.ks_viz_btn)

        # Export JSON (compiled + chunks)
        self.ks_export_btn = QPushButton("Export Changes (JSON)")
        self.ks_export_btn.clicked.connect(self.ks_export_changes)
        layout.addWidget(self.ks_export_btn)

        # Export Timeline CSV (row per edit)
        self.ks_export_csv_btn = QPushButton("Export Timeline CSV")
        self.ks_export_csv_btn.clicked.connect(self.ks_export_timeline_csv)
        layout.addWidget(self.ks_export_csv_btn)

        # Compute metrics
        self.ks_metrics_btn = QPushButton("Compute Metrics (per actor)")
        self.ks_metrics_btn.clicked.connect(self.ks_compute_metrics)
        layout.addWidget(self.ks_metrics_btn)

        # Maintenance / Diagnostics
        self.ks_maint_btn = QPushButton("Maintenance: Fix Log Timestamps")
        self.ks_maint_btn.clicked.connect(self.ks_run_maintenance)
        layout.addWidget(self.ks_maint_btn)

        self.ks_diag_btn = QPushButton("Diagnostics")
        self.ks_diag_btn.clicked.connect(self.ks_run_diagnostics)
        layout.addWidget(self.ks_diag_btn)

        self.tabs.addTab(ks_tab, "Knowledge Space")

    def create_ks_quickrun_tab(self):
        """A separate place (NOT in the main list) with a one-click full pipeline button."""
        quick_tab = QWidget()
        layout = QVBoxLayout(quick_tab)

        layout.addWidget(QLabel("<b>One-Click Knowledge Space Run</b><br>"
                                "Select a folder and run the full pipeline (review → viz → exports → metrics).<br>"
                                "<i>Diagnostics/Maintenance are intentionally excluded here.</i>"))

        self.ks_quick_folder_btn = QPushButton("Select Folder for Quick Run")
        self.ks_quick_folder_btn.clicked.connect(self.select_ks_quick_folder)
        layout.addWidget(self.ks_quick_folder_btn)

        self.ks_quick_folder_label = QLabel("No folder selected.")
        layout.addWidget(self.ks_quick_folder_label)

        self.ks_quick_run_btn = QPushButton("Run FULL KS Pipeline")
        self.ks_quick_run_btn.clicked.connect(self.ks_run_full_pipeline)
        layout.addWidget(self.ks_quick_run_btn)

        self.tabs.addTab(quick_tab, "KS Quick Run")

    # ----------------- KS helpers & handlers -----------------

    def select_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.selected_pdf = file_path
            self.chat_log.append(f"Selected: {file_path}")

    def select_batch_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder for Batch Review")
        if folder_path:
            self.batch_folder = folder_path
            self.chat_log.append(f"Batch Folder: {folder_path}")

    def select_ks_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Knowledge Space Folder")
        if folder_path:
            self.ks_folder = folder_path
            self.ks_folder_label.setText(f"KS Folder: {folder_path}")
            self.chat_log.append(f"KS Folder set: {folder_path}")

    def select_ks_quick_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder for Quick Run")
        if folder_path:
            self.ks_quick_folder = folder_path
            self.ks_quick_folder_label.setText(f"Quick Run Folder: {folder_path}")
            self.chat_log.append(f"Quick Run Folder: {folder_path}")

    def ks_run_review(self):
        if not hasattr(self, 'ks_folder'):
            self.chat_log.append("⚠️ No KS folder selected.")
            return
        mode = self.ask_ks_mode("Knowledge Space Review")
        if mode is None:
            return  # canceled
        downloaded = bool(mode)
        try:
            from core.knowledge_space.ingest import review_folder
            self.thread = TaskRunnerThread(review_folder, self.ks_folder, None, "log_only" if downloaded else "auto")
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "KS: Reviewing folder…")
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS review error: {e}")

    def ks_generate_timeline(self):
        # Optional — if you have a dedicated timeline task; otherwise exports cover this
        try:
            from tasks.ks_generate_timeline import run as run_tl
        except Exception:
            self.chat_log.append("ℹ️ No dedicated timeline task found; the Export Changes step already emits a compiled timeline JSON.")
            return

        mode = self.ask_ks_mode("Generate Timeline")
        if mode is None:
            return
        downloaded = bool(mode)
        self.thread = TaskRunnerThread(run_tl, getattr(self, 'ks_folder', None), "", 0, None, downloaded=downloaded)
        self.thread.update_status.connect(self.chat_log.append)
        self.thread.finished.connect(self.task_finished_with_result)
        self._attach_busy(self.thread, "KS: Generating Timeline…")
        self.thread.start()

    def ks_generate_visuals(self):
        # call plotly viz generator directly (works from DB)
        mode = self.ask_ks_mode("Generate Timeline Visualizations")
        if mode is None:
            return
        downloaded = bool(mode)
        try:
            from core.knowledge_space.viz import generate_visualizations
            def _viz_wrapper():
                sources = ["changelog"] if downloaded else None
                path = generate_visualizations(sources=sources, label="logs" if downloaded else "local")
                return True, f"Visualizations generated. Opened: {path}"
            self.thread = TaskRunnerThread(_viz_wrapper)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "KS: Generating Visuals…")
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS viz error: {e}")

    def ks_export_changes(self):
        mode = self.ask_ks_mode("Export Changes (JSON)")
        if mode is None:
            return
        downloaded = bool(mode)
        try:
            from tasks.export_changes import run as export_run
            self.thread = TaskRunnerThread(export_run, None, "", 0, None, downloaded=downloaded)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "KS: Exporting changes…")
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS export error: {e}")

    def ks_export_timeline_csv(self):
        try:
            from tasks.export_timeline_csv import run as csv_run
            self.thread = TaskRunnerThread(csv_run, None, "", 0, None)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "KS: Exporting timeline…")
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS CSV export error: {e}")

    def ks_compute_metrics(self):
        try:
            from tasks.compute_metrics import run as met_run
            self.thread = TaskRunnerThread(met_run, None, "", 0, None)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "KS: Computing metrics…")
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS metrics error: {e}")

    def ks_run_maintenance(self):
        try:
            from tasks.ks_fix_changelog_ts import run as fix_ts
            self.thread = TaskRunnerThread(fix_ts, None, "", 0, None, downloaded=False)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "KS: Running maintenance…")
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS maintenance error: {e}")

    def ks_run_diagnostics(self):
        try:
            from tasks.ks_diagnose import run as diag_run
            self.thread = TaskRunnerThread(diag_run, None, "", 0, None, downloaded=False)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "KS: Running diagnostics…")
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS diagnostics error: {e}")

    def ks_run_full_pipeline(self):
        """
        Runs: review -> visualizations -> export JSON -> export CSV timeline -> compute metrics
        on the selected quick-run folder (separate from the main KS tab).
        """
        if not hasattr(self, 'ks_quick_folder'):
            self.chat_log.append("⚠️ No Quick Run folder selected.")
            return

        mode = self.ask_ks_mode("Full KS Pipeline")
        if mode is None:
            return
        downloaded = bool(mode)

        # Build steps
        steps = []
        # 1) Review
        try:
            from core.knowledge_space.ingest import review_folder
            steps.append(("Knowledge Space Review",
                          lambda root, m: review_folder(root, None, m),
                          {"root": self.ks_quick_folder, "m": "log_only" if downloaded else "auto"}))
        except Exception:
            self.chat_log.append("⚠️ Review step not available; skipping.")

        # 2) Visualizations
        try:
            from core.knowledge_space.viz import generate_visualizations
            steps.append(("Generate Visualizations",
                          lambda sources, label: (True, f"Saved visuals at {generate_visualizations(sources=sources, label=label)}"),
                          {"sources": ["changelog"] if downloaded else None, "label": "logs" if downloaded else "local"}))
        except Exception:
            self.chat_log.append("⚠️ Visualization step not available; skipping.")

        # 3) Export JSON
        try:
            from tasks.export_changes import run as export_run
            steps.append(("Export Changes (JSON)",
                          lambda d: export_run(None, "", 0, None, downloaded=d),
                          {"d": downloaded}))
        except Exception:
            self.chat_log.append("⚠️ Export JSON step not available; skipping.")

        # 4) Export Timeline CSV
        try:
            from tasks.export_timeline_csv import run as csv_run
            steps.append(("Export Timeline CSV",
                          lambda: csv_run(None, "", 0, None, False),
                          {}))
        except Exception:
            self.chat_log.append("⚠️ Timeline CSV step not available; skipping.")

        # 5) Compute Metrics
        try:
            from tasks.compute_metrics import run as met_run
            steps.append(("Compute Metrics",
                          lambda: met_run(None, "", 0, None, False),
                          {}))
        except Exception:
            self.chat_log.append("⚠️ Metrics step not available; skipping.")

        if not steps:
            self.chat_log.append("⚠️ No steps available in pipeline.")
            return

        # Kick off pipeline
        def _adapt(label, fn, kwargs):
            # wrap call signature to (ok,msg)
            def _runner():
                res = fn(**kwargs)
                if isinstance(res, tuple) and len(res) == 2:
                    return res
                return True, f"{label} completed."
            return _runner

        runnable_steps = []
        for label, fn, kwargs in steps:
            runnable_steps.append((label, _adapt(label, fn, kwargs), {}))

        # Use a dedicated pipeline thread to show step-by-step progress
        self.pipeline_thread = PipelineRunnerThread([(lbl, func, kw) for (lbl, func, kw) in runnable_steps])
        self.pipeline_thread.update_status.connect(self.chat_log.append)
        self.pipeline_thread.finished.connect(self.task_finished_with_result)
        self.pipeline_thread.start()

    # ----------------- Lit Review & Misc -----------------

    def run_literature_review(self):
        if hasattr(self, 'selected_pdf'):
            guidance = self.guidance_input.toPlainText()
            self.progress_bar.setVisible(True)
            self.run_button.setEnabled(False)
            self.chat_log.append("Running review...")

            recall_depth = 5
            try:
                recall_text = self.recall_input.text().strip()
                if recall_text:
                    recall_depth = int(recall_text)
            except ValueError:
                self.chat_log.append("⚠️ Invalid recall depth entered. Using default of 5.")

            self.thread = TaskRunnerThread(run_litreview, self.selected_pdf, guidance, recall_depth, self.output_file_path)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self._attach_busy(self.thread, "Lit: Conducting review…")
            self.thread.start()
        else:
            self.chat_log.append("No PDF selected.")

    def task_finished_with_result(self, success, message):
        self.progress_bar.setVisible(False)
        try:
            self.run_button.setEnabled(True)
        except Exception:
            pass
        try:
            self.batch_run_button.setEnabled(True)
        except Exception:
            pass
        if success:
            self.chat_log.append(f"✅ {message}")
            # If the task returned a “CSV written: <path> …” message, remember its folder.
            try:
                # Expected format: 'CSV written: <full_path>  (raw: N, deduped: M)'
                if "CSV written:" in message:
                    path_part = message.split("CSV written:", 1)[1].strip()
                    out_path = path_part.split("  (", 1)[0].strip()
                    if os.path.exists(out_path):
                        self._ls_last_out_dir = os.path.dirname(out_path)
                        self.btn_ls_open.setEnabled(True)
            except Exception:
                pass
        else:
            self.chat_log.append(f"❌ Task failed: {message}")

    def run_batch_review(self):
        if hasattr(self, 'batch_folder'):
            self.progress_bar.setVisible(True)
            self.batch_run_button.setEnabled(False)
            self.chat_log.append("Starting batch review...")

            self.thread = TaskRunnerThread(run_batch_litreview, self.batch_folder, self.output_file_path)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished)
            self._attach_busy(self.thread, "Lit: Running batch review…")
            self.thread.start()
        else:
            self.chat_log.append("No batch folder selected.")

    def task_finished(self):
        self.progress_bar.setVisible(False)
        try:
            self.run_button.setEnabled(True)
            self.batch_run_button.setEnabled(True)
        except Exception:
            pass
        self.chat_log.append("Task finished.")

    def import_review_memory(self):
        self.chat_log.append("Loading review memory...")
        try:
            load_reviews_to_memory()
            self.chat_log.append("Review memory loaded.")
        except Exception as e:
            self.chat_log.append(f"Error loading memory: {e}")



    def create_chat_tab(self):
        chat_tab = QWidget()
        layout = QVBoxLayout(chat_tab)

        layout.addWidget(QLabel("Conversation with Ailys (approval-gated via artificial cognition)"))

        # Session owned by this tab
        self.chat_session = ChatSession()  # you can expose temperature/max_tokens in UI later

        # Controls
        btn_row = QHBoxLayout()
        self.btn_chat_new = QPushButton("New Chat")
        self.btn_chat_export = QPushButton("Export Transcript")
        btn_row.addWidget(self.btn_chat_new)
        btn_row.addWidget(self.btn_chat_export)
        layout.addLayout(btn_row)

        # Display & input
        self.chat_display = QTextEdit();
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your message to Ailys…")
        layout.addWidget(self.chat_input)

        self.btn_chat_send = QPushButton("Send")
        self.btn_chat_send.clicked.connect(self.send_chat_message)
        # new chat: ask the task to reset, and just clear the local display
        self.btn_chat_new.clicked.connect(lambda: self._chat_reset_via_task())
        # export: GUI only opens the file dialog; task does the saving + returns status
        self.btn_chat_export.clicked.connect(lambda: self._chat_export_via_task())

        layout.addWidget(self.btn_chat_send)

        self.tabs.addTab(chat_tab, "Chat")

    def send_chat_message(self):
        message = self.chat_input.toPlainText().strip()
        if not message:
            return
        self.chat_display.append(f"You: {message}")
        self.chat_input.clear()

        self.chat_display.append("Ailys is thinking... (may require approval)")

        def _task():
            try:
                reply = self.chat_session.send(message, description="GUI Chat")
                return True, reply
            except Exception as e:
                return False, str(e)

        self.chat_thread = TaskRunnerThread(_task)
        self.chat_thread.finished.connect(
            lambda ok, msg: self.chat_display.append(f"Ailys: {msg.strip()}" if ok else f"❌ Error: {msg}")
        )
        self.chat_thread.start()

    def _chat_reset_via_task(self):
        # Task owns reset; GUI just updates visuals with the returned banner
        banner = self.chat_session.reset_and_return_banner()
        self.chat_display.clear()
        self.chat_log.append(banner)

    def _chat_export_via_task(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chat Transcript", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            status = self.chat_session.save_transcript(path)  # task does the saving and returns status text
            self.chat_log.append(status)
        except Exception as e:
            self.chat_log.append(f"❌ Export failed: {e}")

def launch_gui():
    app = QApplication(sys.argv)
    window = AilysGUI()
    window.show()
    sys.exit(app.exec())
