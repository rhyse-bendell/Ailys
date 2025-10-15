import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QTabWidget, QLabel, QHBoxLayout, QTextEdit, QComboBox, QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QMessageBox

from tasks.literature_review import run as run_litreview
from core.batch import run_batch_litreview
from memory_loader import load_reviews_to_memory
from core.approval_queue import approval_queue
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl


_client = None
def get_openai_client():
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is not set.")
        _client = OpenAI(api_key=key)
    return _client


output_file_path = "C2_Lit_Review.xlsx"


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



class AilysGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ailys - Modular Assistant")
        self.resize(1000, 600)
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(650)
        main_layout.addWidget(self.tabs, 3)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setPlaceholderText("Ailys will report messages and updates here.")
        self.chat_log.setMinimumWidth(350)
        main_layout.addWidget(self.chat_log, 2)

        # Existing tabs
        self.create_main_tab()
        self.create_literature_tab()
        self.create_batch_tab()
        self.create_memory_tab()
        self.create_chat_tab()

        # NEW: Knowledge Space tab
        self.create_knowledge_space_tab()

        # Approvals tab last, as before
        self.create_approvals_tab()

        # Approval reminder ticker
        from PySide6.QtCore import QTimer
        self.approval_timer = QTimer()
        self.approval_timer.timeout.connect(self.check_approval_notifications)
        self.approval_timer.start(5000)  # every 5 seconds

    def check_approval_notifications(self):
        pending = approval_queue.get_pending_requests()
        if pending:
            self.chat_log.append(f"⚠️ {len(pending)} approval request(s) pending.")
            # chat_display is created in the Chat tab
            self.chat_display.append(
                f"⚠️ Ailys: You have {len(pending)} API request(s) waiting for approval in the Approvals tab.")

    def create_main_tab(self):
        main_tab = QWidget()
        layout = QVBoxLayout(main_tab)
        layout.addWidget(QLabel("Welcome to Ailys. Select a task tab above to get started."))
        self.tabs.addTab(main_tab, "Main")

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

    def create_approvals_tab(self):
        approval_tab = QWidget()
        layout = QVBoxLayout(approval_tab)

        self.approval_refresh_button = QPushButton("Refresh Pending Approvals")
        self.approval_refresh_button.clicked.connect(self.display_pending_approvals)
        layout.addWidget(self.approval_refresh_button)

        self.approval_log = QTextEdit()
        self.approval_log.setReadOnly(True)
        self.approval_log.setPlaceholderText("Pending API requests requiring approval will appear here.")
        layout.addWidget(self.approval_log)

        self.approve_next_button = QPushButton("Approve Next Request")
        self.approve_next_button.clicked.connect(self.approve_next_request)
        layout.addWidget(self.approve_next_button)

        self.bulk_approve_input = QLineEdit()
        self.bulk_approve_input.setPlaceholderText("Enter number to bulk approve (e.g., 10)")
        layout.addWidget(self.bulk_approve_input)

        self.bulk_approve_button = QPushButton("Bulk Approve N Requests")
        self.bulk_approve_button.clicked.connect(self.bulk_approve_requests)
        layout.addWidget(self.bulk_approve_button)

        self.tabs.addTab(approval_tab, "Approvals")

    def create_chat_tab(self):
        chat_tab = QWidget()
        layout = QVBoxLayout(chat_tab)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(QLabel("Conversation with Ailys (GPT-4)"))

        self.chat_mode_selector = QComboBox()
        self.chat_mode_selector.addItems(["Approval Required", "Direct Chat"])
        layout.addWidget(QLabel("Chat Mode"))
        layout.addWidget(self.chat_mode_selector)

        layout.addWidget(self.chat_display)

        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your message to Ailys...")
        layout.addWidget(self.chat_input)

        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_chat_message)

        layout.addWidget(send_button)

        self.tabs.addTab(chat_tab, "GPT Chat")

    # ---------- NEW: Knowledge Space tab ----------
    def create_knowledge_space_tab(self):
        ks_tab = QWidget()
        layout = QVBoxLayout(ks_tab)

        self.ks_root_label = QLabel("No folder selected.")
        layout.addWidget(self.ks_root_label)

        self.ks_folder_btn = QPushButton("Select Folder to Review")
        self.ks_folder_btn.clicked.connect(self.ks_select_folder)
        layout.addWidget(self.ks_folder_btn)

        self.ks_run_review_btn = QPushButton("Run Knowledge Space Review")
        self.ks_run_review_btn.clicked.connect(self.ks_run_review)
        layout.addWidget(self.ks_run_review_btn)

        self.ks_run_timeline_btn = QPushButton("Generate Timeline")
        self.ks_run_timeline_btn.clicked.connect(self.ks_run_timeline)
        layout.addWidget(self.ks_run_timeline_btn)

        self.ks_run_viz_btn = QPushButton("Generate Timeline Visualizations")
        self.ks_run_viz_btn.clicked.connect(self.ks_run_timeline_visuals)
        layout.addWidget(self.ks_run_viz_btn)

        self.ks_export_btn = QPushButton("Export Changes (JSON)")
        self.ks_export_btn.clicked.connect(self.ks_export_changes)
        layout.addWidget(self.ks_export_btn)

        # Export Timeline CSV
        self.ks_export_csv_btn = QPushButton("Export Timeline CSV")
        self.ks_export_csv_btn.clicked.connect(self.ks_export_timeline_csv)
        layout.addWidget(self.ks_export_csv_btn)

        # Compute Metrics
        self.ks_metrics_btn = QPushButton("Compute Metrics (per actor)")
        self.ks_metrics_btn.clicked.connect(self.ks_compute_metrics)
        layout.addWidget(self.ks_metrics_btn)

        self.ks_maintenance_btn = QPushButton("Maintenance: Fix Log Timestamps")
        self.ks_maintenance_btn.clicked.connect(self.ks_run_maintenance)
        layout.addWidget(self.ks_maintenance_btn)

        from PySide6.QtWidgets import QCheckBox
        self.ks_downloaded_checkbox = QCheckBox("Downloaded space (use change logs only)")
        self.ks_downloaded_checkbox.setChecked(False)
        layout.addWidget(self.ks_downloaded_checkbox)


        self.tabs.addTab(ks_tab, "Knowledge Space")



    # ---------- Knowledge Space handlers ----------

    def ks_export_timeline_csv(self):
        try:
            from tasks.export_timeline_csv import run as csv_run
            # No need to ask logs/local here — CSV includes both sources so you can filter later.
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

    def ks_select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Knowledge Review")
        if folder:
            self.ks_folder = folder
            self.ks_root_label.setText(f"Root: {folder}")
            self.chat_log.append(f"Knowledge Space Root: {folder}")

    def ks_export_changes(self):
        try:
            from tasks.export_changes import run as export_run
            # Ask which source view to export (same prompt you added earlier)
            from PySide6.QtWidgets import QMessageBox
            downloaded = self.ask_ks_mode("Export Changes (JSON)")
            self.thread = TaskRunnerThread(export_run, None, "", 0, None, downloaded=downloaded)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS export error: {e}")

    def ks_run_review(self):
        if not hasattr(self, "ks_folder"):
            self.chat_log.append("⚠️ Select a folder first.")
            return
        try:
            from tasks.knowledge_space_review import run as ks_run
            downloaded = self.ask_ks_mode("Knowledge Space Review")
            mode_note = "log_only (change logs)" if downloaded else "auto (local filesystem)"
            self.chat_log.append(f"Review mode selected: {mode_note}")
            self.thread = TaskRunnerThread(ks_run, self.ks_folder, "", 0, None, downloaded=downloaded)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS review error: {e}")

    def ks_run_timeline(self):
        try:
            from tasks.generate_timeline import run as tl_run
            downloaded = self.ask_ks_mode("Generate Timeline")
            mode_note = "change logs only" if downloaded else "all events (local + logs)"
            self.chat_log.append(f"Timeline mode selected: {mode_note}")
            self.thread = TaskRunnerThread(tl_run, None, "", 0, None, downloaded=downloaded)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS timeline error: {e}")

    def ks_run_timeline_visuals(self):
        try:
            from tasks.generate_timeline_visuals import run as viz_run
            downloaded = self.ask_ks_mode("Generate Timeline Visualizations")
            mode_note = "log-only view will open" if downloaded else "local view will open"
            self.chat_log.append(f"Visualization mode selected: {mode_note}")
            # This task always generates BOTH views; the flag just chooses which to auto-open.
            self.thread = TaskRunnerThread(viz_run, None, "", 0, None, downloaded=downloaded)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.ks_viz_finished)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS viz error: {e}")

    def ks_run_maintenance(self):
        try:
            from tasks.ks_fix_changelog_ts import run as fix_run
            # No params needed; it operates on the existing KS DB
            self.thread = TaskRunnerThread(fix_run, None, "", 0, None)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        except Exception as e:
            self.chat_log.append(f"❌ KS maintenance error: {e}")

    def ask_ks_mode(self, title: str) -> bool:
        """
        Ask the user which source to use.
        Returns True  -> use change logs (downloaded/archival)
                False -> use local filesystem edits (live/local)
        """
        mb = QMessageBox(self)
        mb.setWindowTitle(title)
        mb.setText("How should I build this?")
        mb.setInformativeText(
            "• Use change logs (downloaded/archival)\n"
            "• Use local filesystem edits (live workspace)"
        )
        logs_btn = mb.addButton("Use change logs", QMessageBox.AcceptRole)
        local_btn = mb.addButton("Use local filesystem", QMessageBox.ActionRole)
        mb.setDefaultButton(logs_btn)
        mb.exec()
        return mb.clickedButton() is logs_btn

    def ks_viz_finished(self, success, message):
        self.task_finished_with_result(success, message)
        if not success:
            return

        # Extract both paths if present
        def _extract(marker):
            return message.split(marker, 1)[1].split()[0] if marker in message else None

        path_primary = _extract("PRIMARY=")
        path_local = _extract("GLOBAL_LOCAL=")
        path_logs = _extract("GLOBAL_LOGS=")

        # Auto-open primary (local view if checkbox OFF, logs view if checkbox ON)
        path = path_primary or path_local or path_logs
        if path and os.path.exists(path):
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path)))
            self.chat_log.append(f"🖼 Opened: {path}")
        else:
            self.chat_log.append(f"⚠️ Visualization not found at: {path}")

        # Also show where both versions were saved
        if path_local:
            self.chat_log.append(f"Local view: {path_local}")
        if path_logs:
            self.chat_log.append(f"Log-only view: {path_logs}")

    # ---------- Existing helpers ----------


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

            self.thread = TaskRunnerThread(run_litreview, self.selected_pdf, guidance, recall_depth, output_file_path)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished_with_result)
            self.thread.start()
        else:
            self.chat_log.append("No PDF selected.")

    def task_finished_with_result(self, success, message):
        self.progress_bar.setVisible(False)
        # These buttons may not exist in non-active tabs; guard where needed
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

            self.thread = TaskRunnerThread(run_batch_litreview, self.batch_folder, output_file_path)
            self.thread.update_status.connect(self.chat_log.append)
            self.thread.finished.connect(self.task_finished)
            self.thread.start()
        else:
            self.chat_log.append("No batch folder selected.")

    def task_finished(self):
        self.progress_bar.setVisible(False)
        try:
            self.run_button.setEnabled(True)
        except Exception:
            pass
        try:
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

    def display_pending_approvals(self):
        pending = approval_queue.get_pending_requests()
        if not pending:
            self.approval_log.setPlainText("No pending approvals.")
            return
        self.approval_log.setPlainText("\n".join([f"[{r.id}] {r.description}" for r in pending]))

    def approve_next_request(self):
        pending = approval_queue.get_pending_requests()
        if pending:
            approval_queue.approve_request(pending[0].id)
            self.chat_log.append(f"✅ Approved request {pending[0].id}: {pending[0].description}")
        else:
            self.chat_log.append("⚠️ No pending requests.")
        self.display_pending_approvals()

    def bulk_approve_requests(self):
        try:
            count = int(self.bulk_approve_input.text().strip())
            approval_queue.approve_batch(count)
            self.chat_log.append(f"✅ Approved next {count} requests.")
        except ValueError:
            self.chat_log.append("⚠️ Invalid number entered.")
        self.display_pending_approvals()

    def send_gpt_chat_message(self):
        user_input = self.chat_input.toPlainText().strip()
        if not user_input:
            return

        self.chat_display.append(f"🧑 You: {user_input}")
        self.chat_input.clear()

        try:
            client = get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": user_input}],
                temperature=0.3
            )
            reply = response.choices[0].message.content.strip()
            self.chat_display.append(f"🤖 Ailys: {reply}")
        except Exception as e:
            self.chat_display.append(f"❌ Error calling GPT: {str(e)}")

    def send_chat_message(self):
        message = self.chat_input.toPlainText().strip()
        if not message:
            return

        self.chat_display.append(f"You: {message}")
        self.chat_input.clear()

        mode = self.chat_mode_selector.currentText()

        if mode == "Direct Chat":
            try:
                client = get_openai_client()
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": message}],
                    temperature=0.3
                )
                reply = response.choices[0].message.content.strip()
                self.chat_display.append(f"Ailys: {reply}")
            except Exception as e:
                self.chat_display.append(f"❌ Error calling GPT: {str(e)}")
        else:  # Approval Required
            def call_fn():
                client = get_openai_client()
                completion = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": message}],
                    temperature=0.7
                )
                return completion.choices[0].message.content.strip()

            try:
                self.chat_display.append("Ailys is thinking... (awaiting approval)")
                from core.approval_queue import request_approval
                reply = request_approval(description=f"GPT Chat: '{message}'", call_fn=call_fn)
                if reply:
                    self.chat_display.append(f"Ailys: {reply}")
                else:
                    self.chat_display.append("⚠️ Message not approved or failed.")
            except Exception as e:
                self.chat_display.append(f"❌ Error: {e}")


def launch_gui():
    app = QApplication(sys.argv)
    window = AilysGUI()
    window.show()
    sys.exit(app.exec())
