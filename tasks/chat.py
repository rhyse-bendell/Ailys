# tasks/chat.py
from __future__ import annotations
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from core import artificial_cognition as ac

DEFAULT_SYSTEM = (
    "You are Ailys, a helpful research copilot. Be concise, cite when asked, "
    "and avoid fabricating sources."
)

@dataclass
class ChatSession:
    system_prompt: str = DEFAULT_SYSTEM
    temperature: float = 0.5
    max_tokens: int = 1200
    history: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        if self.system_prompt:
            self.history.append({"role": "system", "content": self.system_prompt})

    # ---- session lifecycle ----
    def reset(self, system_prompt: Optional[str] = None):
        self.history = []
        if system_prompt is not None:
            self.system_prompt = system_prompt
        if self.system_prompt:
            self.history.append({"role": "system", "content": self.system_prompt})

    def reset_and_return_banner(self) -> str:
        """Resets and returns a user-facing banner string for the GUI log."""
        self.reset()
        return "🧹 Started a new chat session."

    # ---- core action ----
    def send(self, user_text: str, *, description: str = "Chat message") -> str:
        if not user_text or not user_text.strip():
            return ""
        self.history.append({"role": "user", "content": user_text})
        result = ac.ask(
            messages=self.history,
            description=f"{description} (Chat)",
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        reply = result.raw_text or ""
        self.history.append({"role": "assistant", "content": reply})
        return reply

    # ---- transcript utilities ----
    def transcript_text(self) -> str:
        lines = []
        for m in self.history:
            role = m.get("role", "")
            if role == "system":
                continue
            lines.append(f"{role.capitalize()}: {m.get('content','')}")
        return "\n\n".join(lines)

    def save_transcript(self, path: str) -> str:
        """Save transcript to 'path' and return a short status string."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.transcript_text())
        return f"💾 Transcript saved: {path}"
