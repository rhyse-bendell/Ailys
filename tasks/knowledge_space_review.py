# tasks/knowledge_space_review.py
from core.knowledge_space.ingest import review_folder

def run(root_path, guidance="", recall_depth=0, output_file=None, downloaded=False):
    mode = "log_only" if downloaded else "auto"
    stats = review_folder(root_path, actor_hint="", mode=mode)
    return True, f"Knowledge Space Review ({mode}) complete. Files: {stats['files_seen']} | Edits: {stats['edits']} | Log rows: {stats['log_rows']}"
