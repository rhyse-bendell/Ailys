# tasks/ks_rebuild_participants.py
from core.knowledge_space.participants import backfill_all_participants

def run(root_path=None, guidance="", recall_depth=0, output_file=None, downloaded=False):
    created, total_seen = backfill_all_participants()
    return True, f"Participants backfill complete. New PIDs created: {created} / actors seen: {total_seen}."
