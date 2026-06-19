from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Student TODO: implement a simple token estimator.

    Example idea:
    - Strip whitespace
    - Return 0 for empty text
    - Approximate tokens from character count, e.g. len(text) / 4
    """

    text = text.strip()
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`.

    Student TODO:
    - Map each user id to one markdown file
    - Support read / write / edit operations
    - Optionally expose helpers like `facts()` or `upsert_fact()`
    """

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        import re
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', user_id.lower())
        return self.root_dir / f"{safe_id}.md"

    def read_text(self, user_id: str) -> str:
        p = self.path_for(user_id)
        if p.exists():
            return p.read_text(encoding="utf-8")
        return ""

    def write_text(self, user_id: str, content: str) -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        p = self.path_for(user_id)
        p.write_text(content, encoding="utf-8")
        return p

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        content = self.read_text(user_id)
        if search_text in content:
            new_content = content.replace(search_text, replacement)
            self.write_text(user_id, new_content)
            return True
        return False

    def file_size(self, user_id: str) -> int:
        p = self.path_for(user_id)
        return p.stat().st_size if p.exists() else 0


def extract_profile_updates(message: str) -> dict[str, dict[str, object]]:
    """Student TODO: convert raw user text into stable profile facts.

    Example facts you may want to extract:
    - name
    - location
    - profession
    - preferences / response style
    - favorite food / drink

    Pseudocode:
    1. Build a few regex patterns.
    2. Skip obvious question-only turns.
    3. Return only the facts that are confidently present in the message.
    """

    import re
    facts = {}
    msg_lower = message.lower()
    
    # Conflict handling: Detect if user denies a fact
    if "tôi không phải tên" in msg_lower or "không phải tên là" in msg_lower:
        facts['name'] = {'value': '', 'confidence': 1.0, 'operation': 'delete'}
    elif "tôi không sống ở" in msg_lower or "chuyển đi khỏi" in msg_lower:
        facts['location'] = {'value': '', 'confidence': 1.0, 'operation': 'delete'}
    
    # Extract location
    if 'location' not in facts:
        loc_match = re.search(r'(?:tôi đang sống ở|mình sống ở|chuyển nhà vào|mình ở|tôi ở) ([a-zA-ZÀ-ỹ\s]+)(?:$|\.|,)', message, re.IGNORECASE)
        if loc_match:
            facts['location'] = {'value': loc_match.group(1).strip(), 'confidence': 0.9, 'operation': 'upsert'}

    # Extract name
    if 'name' not in facts:
        name_match = re.search(r'(?:tên tôi là|tôi tên là|mình tên là|gọi tôi là|tên mình là) ([a-zA-ZÀ-ỹ\s]+)(?:$|\.|,)', message, re.IGNORECASE)
        if name_match:
            facts['name'] = {'value': name_match.group(1).strip(), 'confidence': 0.9, 'operation': 'upsert'}
            
    # Simulate a low confidence extraction
    profession_match = re.search(r'(?:tôi làm|mình làm) ([a-zA-ZÀ-ỹ\s]+)(?:$|\.|,)', message, re.IGNORECASE)
    if profession_match and "nghề" not in msg_lower:
        facts['profession'] = {'value': profession_match.group(1).strip(), 'confidence': 0.5, 'operation': 'upsert'}
    elif profession_match and "nghề" in msg_lower:
        facts['profession'] = {'value': profession_match.group(1).strip(), 'confidence': 0.9, 'operation': 'upsert'}
        
    return facts


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Student TODO: create a compact summary of older messages.

    This can be heuristic text concatenation first.
    Later, you can replace it with an LLM-based summary if desired.
    """

    if not messages:
        return ""
    return f"Tóm tắt: Đã nén {len(messages)} tin nhắn cũ."


@dataclass
class CompactMemoryManager:
    """Student TODO: implement compact memory for long threads.

    Goal:
    - Keep recent messages in full
    - When the thread grows too large, move older content into a summary
    - Track how many compactions happened for benchmarking
    """

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        if thread_id not in self.state:
            self.state[thread_id] = {
                "messages": [],
                "summary": "",
                "compactions": 0
            }
        
        thread = self.state[thread_id]
        thread["messages"].append({"role": role, "content": content})
        
        total_tokens = estimate_tokens(thread["summary"]) + sum(estimate_tokens(m["content"]) for m in thread["messages"])
        
        if total_tokens > self.threshold_tokens and len(thread["messages"]) > self.keep_messages:
            messages_to_compress = thread["messages"][:-self.keep_messages]
            kept_messages = thread["messages"][-self.keep_messages:]
            
            new_summary = summarize_messages(messages_to_compress)
            thread["summary"] = new_summary
                
            thread["messages"] = kept_messages
            thread["compactions"] += 1

    def context(self, thread_id: str) -> dict[str, object]:
        return self.state.get(thread_id, {"messages": [], "summary": "", "compactions": 0})

    def compaction_count(self, thread_id: str) -> int:
        return self.state.get(thread_id, {}).get("compactions", 0)
