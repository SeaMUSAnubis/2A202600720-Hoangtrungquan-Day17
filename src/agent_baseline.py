from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Student TODO: implement Agent A.

    Requirements:
    - Within-session memory only
    - No persistent `User.md`
    - Should forget long-term facts across new threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent when dependencies exist.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: return the agent response and token accounting."""

        if self.force_offline:
            return self._reply_offline(thread_id, message)
            
        if not self.langchain_agent:
            self._maybe_build_langchain_agent()
            
        if self.langchain_agent:
            return self._reply_online(thread_id, message)
        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.sessions[thread_id].token_usage if thread_id in self.sessions else 0

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.sessions[thread_id].prompt_tokens_processed if thread_id in self.sessions else 0

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement a simple offline behavior."""

        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
            
        session = self.sessions[thread_id]
        
        prompt_cost = estimate_tokens(message) + sum(estimate_tokens(m["content"]) for m in session.messages)
        session.prompt_tokens_processed += prompt_cost
        
        session.messages.append({"role": "user", "content": message})
        
        reply_content = "Đây là câu trả lời mặc định từ Baseline Agent."
        
        import re
        if "tên" in message.lower():
            for m in reversed(session.messages):
                if m["role"] == "user":
                    name_match = re.search(r'(?:tên tôi là|tôi tên là|mình tên là) ([a-zA-ZÀ-ỹ\s]+)', m["content"], re.IGNORECASE)
                    if name_match:
                        reply_content = f"Bạn tên là {name_match.group(1).strip()}."
                        break
        elif "sống" in message.lower() or "ở đâu" in message.lower():
            for m in reversed(session.messages):
                if m["role"] == "user":
                    loc_match = re.search(r'(?:tôi đang sống ở|mình sống ở|tôi ở) ([a-zA-ZÀ-ỹ\s]+)', m["content"], re.IGNORECASE)
                    if loc_match:
                        reply_content = f"Bạn đang sống ở {loc_match.group(1).strip()}."
                        break
                        
        session.messages.append({"role": "assistant", "content": reply_content})
        
        agent_cost = estimate_tokens(reply_content)
        session.token_usage += agent_cost
        
        return {"content": reply_content}

    def _reply_online(self, thread_id: str, message: str) -> dict[str, Any]:
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
            
        session = self.sessions[thread_id]
        
        prompt_cost = estimate_tokens(message) + sum(estimate_tokens(m["content"]) for m in session.messages)
        session.prompt_tokens_processed += prompt_cost
        
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        lc_msgs = [SystemMessage(content="You are a helpful AI assistant. Keep responses concise.")]
        for m in session.messages:
            if m["role"] == "user":
                lc_msgs.append(HumanMessage(content=m["content"]))
            else:
                lc_msgs.append(AIMessage(content=m["content"]))
        lc_msgs.append(HumanMessage(content=message))
        
        response = self.langchain_agent.invoke(lc_msgs)
        reply_content = str(response.content)
        
        session.messages.append({"role": "user", "content": message})
        session.messages.append({"role": "assistant", "content": reply_content})
        
        agent_cost = estimate_tokens(reply_content)
        session.token_usage += agent_cost
        
        return {"content": reply_content}

    def _maybe_build_langchain_agent(self):
        """Student TODO: optionally wire `create_agent` + `InMemorySaver` here."""
        if not self.force_offline:
            self.langchain_agent = build_chat_model(self.config.model)
