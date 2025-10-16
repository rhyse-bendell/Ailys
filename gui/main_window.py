import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QTabWidget, QLabel, QHBoxLayout, QTextEdit, QComboBox, QProgressBar, QLineEdit,
    QMessageBox, QListWidget
)

from PySide6.QtCore import Qt, QThread, Signal, QTimer


from tasks.literature_review import run as run_litreview
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
try:
    print("GUI approval queue:", approvals._debug_id(), approvals._debug_counts())
except Exception:
    pass


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

        # List of pending approvals
        self.approvals_list = QListWidget()
        right_layout.addWidget(self.approvals_list, 1)

        # Info/status line
        self.approvals_info = QLabel("")
        self.approvals_info.setStyleSheet("color: #555;")
        right_layout.addWidget(self.approvals_info)

        # Controls row
        btn_row = QHBoxLayout()
        self.btn_approve_selected = QPushButton("Approve Selected")
        self.btn_deny_selected = QPushButton("Deny Selected")
        self.btn_refresh_approvals = QPushButton("Refresh")
        btn_row.addWidget(self.btn_approve_selected)
        btn_row.addWidget(self.btn_deny_selected)
        btn_row.addWidget(self.btn_refresh_approvals)
        right_layout.addLayout(btn_row)

        # Wire actions to handlers (defined below)
        self.btn_refresh_approvals.clicked.connect(self.refresh_approvals_pane)
        self.btn_approve_selected.clicked.connect(self.approve_selected_request)
        self.btn_deny_selected.clicked.connect(self.deny_selected_request)

        # Add to the main layout with smaller stretch
        main_layout.addWidget(right_panel, 1)

        # --- Tabs ---
        self.create_main_tab()
        self.create_api_config_tab()

        self.create_lit_search_tab()
        self.create_literature_tab()
        self.create_batch_tab()

        self.create_chat_tab()

        self.create_knowledge_space_tab()
        self.create_ks_quickrun_tab()

        self.create_memory_tab()


        self.approval_timer = QTimer()
        self.approval_timer.timeout.connect(self.check_approval_notifications)
        self.approval_timer.start(5000)  # every 5 seconds
        QTimer.singleShot(200, self.check_approval_notifications)  # kick a first poll
        self.refresh_approvals_pane()

    # ----------------- Common helpers -----------------

    # ---- Approvals pane helpers -------------------------------------------------

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

    def refresh_approvals_pane(self):
        try:
            pending = approvals.get_pending_requests() if hasattr(approvals,
                                                                  "get_pending_requests") else approvals.approval_queue.get_pending_requests()
        except Exception:
            pending = approvals.approval_queue.get_pending_requests()

        self.approvals_list.clear()
        for r in pending:
            self.approvals_list.addItem(f"[{r.id}] {r.description}")

        n = len(pending)
        self.approvals_info.setText(f"Pending approvals: {n}" if n else "No pending approvals.")

    def approve_selected_request(self):
        rid = self._selected_request_id()
        if rid is None:
            self.approvals_info.setText("Select a request to approve.")
            return
        try:
            # use module-level helper if present; fallback to instance
            if hasattr(approvals, "approve_request"):
                approvals.approve_request(rid)
            else:
                approvals.approval_queue.approve_request(rid)
            self.chat_log.append(f"✅ Approved request {rid}.")
        except Exception as e:
            self.chat_log.append(f"❌ Approve error: {e}")
        self.refresh_approvals_pane()

    def deny_selected_request(self):
        rid = self._selected_request_id()
        if rid is None:
            self.approvals_info.setText("Select a request to deny.")
            return
        try:
            # use module-level helper if present; fallback to instance
            ok = approvals.deny_request(rid) if hasattr(approvals,
                                                        "deny_request") else approvals.approval_queue.deny_request(rid)
            if ok is False:
                self.chat_log.append("⚠️ Could not deny request (maybe already resolved).")
            else:
                self.chat_log.append(f"🚫 Denied request {rid}.")
        except Exception as e:
            self.chat_log.append(f"❌ Deny error: {e}")
        self.refresh_approvals_pane()

    def check_approval_notifications(self):
        pending = approvals.approval_queue.get_pending_requests()
        print(f"[GUI timer] queue_id={id(approvals.approval_queue)} pending={len(pending)}")
        if pending:
            self.chat_log.append(f"⚠️ {len(pending)} approval request(s) pending.")
            try:
                self.chat_display.append(
                    f"⚠️ Ailys: You have {len(pending)} API request(s) waiting in the Approvals pane.")
            except Exception:
                pass
        self.refresh_approvals_pane()

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
            }
            try:
                from core.config import save_env_updates
                save_env_updates(updates, self.env_path)
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
        """Creates the Literature Search tab with Stage A–B functionality."""

        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QLabel, QTextEdit,
            QLineEdit, QPushButton, QFileDialog
        )

        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ---- Researcher Name ----------------------------------------------------
        layout.addWidget(QLabel("Researcher"))
        self.ls_researcher = QLineEdit()
        self.ls_researcher.setPlaceholderText("Enter your display name (e.g., Jess)")
        layout.addWidget(self.ls_researcher)

        # ---- Research Prompt ----------------------------------------------------
        layout.addWidget(QLabel("Literature Search Prompt"))
        self.ls_prompt = QTextEdit()
        self.ls_prompt.setPlaceholderText(
            "Describe your literature search goal...\n"
            "Example: I need to find literature on neurodiversity in teams, "
            "especially where AI supports collaboration or task performance."
        )
        layout.addWidget(self.ls_prompt)

        # ---- Optional Clarifications CSV (Stage A) ------------------------------
        layout.addWidget(QLabel("Optional: Clarifications CSV (to merge with prompt)"))
        self.ls_clar_csv = QLineEdit()
        self.ls_clar_csv.setPlaceholderText("Path to existing prompt_to_keywords.csv (optional)")
        layout.addWidget(self.ls_clar_csv)

        btn_browse_clar = QPushButton("Browse…")

        def browse_clar():
            path, _ = QFileDialog.getOpenFileName(self, "Select Clarifications CSV", "", "CSV Files (*.csv)")
            if path:
                self.ls_clar_csv.setText(path)

        btn_browse_clar.clicked.connect(browse_clar)
        layout.addWidget(btn_browse_clar)

        # ---- CSV-1 Path (for Stage B) ------------------------------------------
        layout.addWidget(QLabel("CSV-1: prompt_to_keywords.csv (for Stage B collection)"))
        self.ls_csv1_path = QLineEdit()
        self.ls_csv1_path.setPlaceholderText("Path to prompt_to_keywords.csv")
        layout.addWidget(self.ls_csv1_path)

        btn_browse_csv1 = QPushButton("Browse…")

        def browse_csv1():
            path, _ = QFileDialog.getOpenFileName(self, "Select prompt_to_keywords.csv", "", "CSV Files (*.csv)")
            if path:
                self.ls_csv1_path.setText(path)

        btn_browse_csv1.clicked.connect(browse_csv1)
        layout.addWidget(btn_browse_csv1)

        # ---- Buttons ------------------------------------------------------------
        self.btn_ls_keywords = QPushButton("1) Generate Keywords (CSV-1)")
        self.btn_ls_collect = QPushButton("2) Collect Results (CSV-2)")
        self.btn_ls_filter = QPushButton("3) Filter to Consider (CSV-3)")
        self.btn_ls_open = QPushButton("Open Output Folder")

        layout.addWidget(self.btn_ls_keywords)
        layout.addWidget(self.btn_ls_collect)
        layout.addWidget(self.btn_ls_filter)
        layout.addWidget(self.btn_ls_open)

        # ---- Connect Buttons ----------------------------------------------------
        self.btn_ls_keywords.clicked.connect(self.run_ls_keywords)
        self.btn_ls_collect.clicked.connect(self.run_ls_collect)
        # Filter + Open will be added later
        self.btn_ls_filter.setEnabled(False)
        self.btn_ls_open.setEnabled(False)

        # ---- Add Tab ------------------------------------------------------------
        self.tabs.addTab(tab, "Lit Search")

    # =========================================================================== #
    # -------------------------- Button Handlers -------------------------------- #
    # =========================================================================== #

    def run_ls_keywords(self):
        """Stage A – Prompt → Keywords (CSV-1)."""
        self.chat_log.append("⏳ Waiting for your approval: open the Approvals tab to allow 'Generate Keywords'.")

        prompt = self.ls_prompt.toPlainText().strip()
        clar_csv = self.ls_clar_csv.text().strip() or None
        researcher = self.ls_researcher.text().strip() or "Researcher"

        if not prompt and not clar_csv:
            self.chat_log.append("⚠️ Provide a prompt or a clarifications CSV.")
            return

        def _task():
            from tasks.lit_search_keywords import run as run_keywords
            ok, msg = run_keywords(
                None,
                guidance=prompt,
                clarifications_csv_path=clar_csv,
                researcher=researcher
            )
            return ok, msg

        self.thread = TaskRunnerThread(_task)
        self.thread.update_status.connect(self.chat_log.append)
        self.thread.finished.connect(self.task_finished_with_result)
        self.thread.start()

    def run_ls_collect(self):
        """Stage B – Keywords → Candidate Records (CSV-2)."""
        csv1 = self.ls_csv1_path.text().strip()
        researcher = self.ls_researcher.text().strip() or None

        if not csv1:
            self.chat_log.append("⚠️ Please select the CSV-1 file (prompt_to_keywords.csv).")
            return

        def _task():
            from tasks.lit_search_collect import run as run_collect
            ok, msg = run_collect(csv1_path=csv1, researcher=researcher, per_source=20)
            return ok, msg

        self.thread = TaskRunnerThread(_task)
        self.thread.update_status.connect(self.chat_log.append)
        self.thread.finished.connect(self.task_finished_with_result)
        self.thread.start()

    def create_literature_tab(self):
        lit_tab = QWidget()
        layout = QVBoxLayout(lit_tab)

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

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

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
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS export error: {e}")

    def ks_export_timeline_csv(self):
        try:
            from tasks.export_timeline_csv import run as csv_run
            self.thread = TaskRunnerThread(csv_run, None, "", 0, None)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS CSV export error: {e}")

    def ks_compute_metrics(self):
        try:
            from tasks.compute_metrics import run as met_run
            self.thread = TaskRunnerThread(met_run, None, "", 0, None)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS metrics error: {e}")

    def ks_run_maintenance(self):
        try:
            from tasks.ks_fix_changelog_ts import run as fix_ts
            self.thread = TaskRunnerThread(fix_ts, None, "", 0, None, downloaded=False)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS maintenance error: {e}")

    def ks_run_diagnostics(self):
        try:
            from tasks.ks_diagnose import run as diag_run
            self.thread = TaskRunnerThread(diag_run, None, "", 0, None, downloaded=False)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
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

        try:
            self.chat_display.append("Ailys is thinking... (may require approval)")
            reply = self.chat_session.send(message, description="GUI Chat")
            self.chat_display.append(f"Ailys: {reply.strip()}")
        except Exception as e:
            self.chat_display.append(f"❌ Error: {e}")

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
