import os
import json
import hashlib
import pandas as pd
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath("memory"))
from memory.memory import save_memory_event

from core.approval_queue import request_approval  # ✅ add this near the top with other imports

# Load environment variables
load_dotenv()

_client = None
def get_openai_client():
    global _client
    if _client is None:
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is not set")
        _client = OpenAI(api_key=key)
    return _client

REVIEW_DIR = "reference_docs/processed_reviews"
GENERATE_INSIGHTS = False  # Toggle to True to use OpenAI for memory insight generation

def hash_content(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()



def generate_insight_from_row(row_text):
    prompt = f"""
You are Ailys, a memory encoding assistant. Given the following structured review of a research article, generate a 3–5 sentence summary of what this article adds to your long-term memory about team cognition, mental models, or team measurement.

Only return the insight. Do not summarize the instructions.

Structured Review:
{row_text}
"""
    return request_approval(
        description="Generate insight from imported memory row",
        call_fn=lambda: get_openai_client().chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
    ).choices[0].message.content.strip()


def load_xlsx(filepath):
    df = pd.read_excel(filepath)
    for idx, row in df.iterrows():
        try:
            content = "\n".join([f"{col}: {row[col]}" for col in df.columns if pd.notnull(row[col])])
            ai_insight = generate_insight_from_row(content) if GENERATE_INSIGHTS else "Imported without GPT summary."
            save_memory_event(
                event_type="literature_review",
                source_text=content,
                ai_insight=ai_insight,
                user_input="Imported from spreadsheet",
                tags=["literature_review", "imported"],
                file_path=os.path.abspath(filepath)
            )
        except Exception as e:
            print(f"Skipping row {idx} in {filepath} due to error: {e}")

def load_jsonl(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                memory = json.loads(line.strip())
                save_memory_event(
                    event_type=memory.get("event_type", "imported"),
                    source_text=memory.get("source_text", "")[:3000],
                    ai_insight=memory.get("ai_insight", "Imported insight."),
                    user_input=memory.get("user_input", "Imported from JSONL"),
                    tags=memory.get("tags", ["imported"]),
                    file_path=os.path.abspath(filepath)
                )
            except Exception as e:
                print(f"Error loading memory from {filepath}: {e}")

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            for memory in data:
                save_memory_event(
                    event_type=memory.get("event_type", "imported"),
                    source_text=memory.get("source_text", "")[:3000],
                    ai_insight=memory.get("ai_insight", "Imported insight."),
                    user_input=memory.get("user_input", "Imported from JSON"),
                    tags=memory.get("tags", ["imported"]),
                    file_path=os.path.abspath(filepath)
                )
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

def load_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        ai_insight = generate_insight_from_row(content) if GENERATE_INSIGHTS else "Imported unstructured note."
        save_memory_event(
            event_type="note",
            source_text=content[:3000],
            ai_insight=ai_insight,
            user_input="Imported from TXT",
            tags=["note", "imported"],
            file_path=os.path.abspath(filepath)
        )
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

def load_reviews_to_memory():
    for filename in os.listdir(REVIEW_DIR):
        filepath = os.path.join(REVIEW_DIR, filename)
        if filename.endswith(".xlsx"):
            load_xlsx(filepath)
        elif filename.endswith(".jsonl"):
            load_jsonl(filepath)
        elif filename.endswith(".json"):
            load_json(filepath)
        elif filename.endswith(".txt"):
            load_txt(filepath)
        else:
            print(f"Skipped unsupported file: {filename}")

if __name__ == "__main__":
    load_reviews_to_memory()
