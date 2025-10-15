import importlib.util
import os

class TaskManager:
    def __init__(self, task_dir="tasks"):
        self.task_dir = task_dir

    def get_available_tasks(self):
        return [f.replace(".py", "") for f in os.listdir(self.task_dir) if f.endswith(".py")]

    def load_task(self, task_name):
        spec = importlib.util.spec_from_file_location(task_name, os.path.join(self.task_dir, f"{task_name}.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
