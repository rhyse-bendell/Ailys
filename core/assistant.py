
from core.task_manager import TaskManager

class Assistant:
    def __init__(self):
        self.task_manager = TaskManager()

    def get_task_names(self):
        return self.task_manager.get_available_tasks()

    def run_task(self, task_name, file_path, prompt, recall_depth=5, output_file=None):
        task_module = self.task_manager.load_task(task_name)
        if hasattr(task_module, "run"):
            task_module.run(file_path, guidance=prompt, recall_depth=recall_depth, output_file=output_file)

    def run_batch(self, task_name, folder, prompt, recall_depth=5, output_file=None):
        from core.batch import run_batch_litreview
        return run_batch_litreview(folder, prompt, recall_depth, output_file)
