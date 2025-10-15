# tasks/generate_timeline_visuals.py
from core.knowledge_space.viz import generate_visualizations

def run(root_path=None, guidance="", recall_depth=0, output_file=None, downloaded=False):
    # Always generate both views
    path_local = generate_visualizations(sources=None, label="local")
    path_logs  = generate_visualizations(sources=["changelog"], label="logs")
    primary = path_logs if downloaded else path_local
    return True, f"Timeline visualizations generated. GLOBAL_LOCAL={path_local} GLOBAL_LOGS={path_logs} PRIMARY={primary}"
