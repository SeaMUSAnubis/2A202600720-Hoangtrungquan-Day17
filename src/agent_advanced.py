from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Student TODO: implement Agent B / Advanced Agent.

    Required memory layers:
    1. within-session memory
    2. persistent `User.md`
    3. compact memory for long threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}

        # TODO: optionally initialize a real LangChain/LangGraph agent.
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        if self.force_offline:
            return self._reply_offline(user_id, thread_id, message)
            
        if not self.langchain_agent:
            self._maybe_build_langchain_agent()
            
        if self.langchain_agent:
            return self._reply_online(user_id, thread_id, message)
        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement the deterministic advanced path."""

        # 1. Extract stable profile facts from the incoming message.
        updates = extract_profile_updates(message)
        
        # 2. Persist those facts into `User.md`.
        if updates:
            content = self.profile_store.read_text(user_id)
            for k, info in updates.items():
                if info['confidence'] >= 0.8:
                    if info['operation'] == 'delete':
                        import re
                        content = re.sub(rf"{k}:.*\n?", "", content)
                    elif info['operation'] == 'upsert':
                        v = info['value']
                        if f"{k}:" in content:
                            import re
                            content = re.sub(rf"{k}:.*", f"{k}: {v}", content)
                        else:
                            content += f"{k}: {v}\n"
            self.profile_store.write_text(user_id, content.strip() + "\n")

        # 3. Append the message into compact memory.
        self.compact_memory.append(thread_id, "user", message)

        # 4. Estimate prompt-context load from `User.md` + summary + recent messages.
        prompt_cost = self._estimate_prompt_context_tokens(user_id, thread_id)
        if thread_id not in self.thread_prompt_tokens:
            self.thread_prompt_tokens[thread_id] = 0
        self.thread_prompt_tokens[thread_id] += prompt_cost

        # 5. Generate a response that can answer long-term recall questions.
        reply_content = self._offline_response(user_id, thread_id, message)

        # 6. Append the assistant reply and update token counters.
        self.compact_memory.append(thread_id, "assistant", reply_content)
        
        agent_cost = estimate_tokens(reply_content)
        if thread_id not in self.thread_tokens:
            self.thread_tokens[thread_id] = 0
        self.thread_tokens[thread_id] += agent_cost

        return {"content": reply_content}

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Student TODO: estimate the context carried into one turn."""

        user_md_tokens = estimate_tokens(self.profile_store.read_text(user_id))
        ctx = self.compact_memory.context(thread_id)
        summary_tokens = estimate_tokens(ctx["summary"])
        recent_tokens = sum(estimate_tokens(m["content"]) for m in ctx["messages"])
        return user_md_tokens + summary_tokens + recent_tokens

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        """Student TODO: return a deterministic answer using persisted memory."""

        msg_lower = message.lower()
        user_md = self.profile_store.read_text(user_id).lower()
        
        if "tên gì" in msg_lower or "tên mình" in msg_lower or "tên tôi" in msg_lower:
            import re
            m = re.search(r"name:\s*(.+)", user_md)
            if m:
                return f"Bạn tên là {m.group(1).title()}."
                
        if "nghề gì" in msg_lower or "công việc" in msg_lower or "làm nghề" in msg_lower:
            import re
            m = re.search(r"profession:\s*(.+)", user_md)
            if m:
                return f"Bạn làm nghề {m.group(1)}."
                
        if "sống ở" in msg_lower or "ở đâu" in msg_lower:
            import re
            m = re.search(r"location:\s*(.+)", user_md)
            if m:
                return f"Bạn sống ở {m.group(1)}."

        return "Đây là câu trả lời mặc định từ Advanced Agent."

    def _reply_online(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        updates = extract_profile_updates(message)
        if updates:
            content = self.profile_store.read_text(user_id)
            for k, info in updates.items():
                if info['confidence'] >= 0.8:
                    if info['operation'] == 'delete':
                        import re
                        content = re.sub(rf"{k}:.*\n?", "", content)
                    elif info['operation'] == 'upsert':
                        v = info['value']
                        if f"{k}:" in content:
                            import re
                            content = re.sub(rf"{k}:.*", f"{k}: {v}", content)
                        else:
                            content += f"{k}: {v}\n"
            self.profile_store.write_text(user_id, content.strip() + "\n")

        self.compact_memory.append(thread_id, "user", message)
        
        prompt_cost = self._estimate_prompt_context_tokens(user_id, thread_id)
        if thread_id not in self.thread_prompt_tokens:
            self.thread_prompt_tokens[thread_id] = 0
        self.thread_prompt_tokens[thread_id] += prompt_cost
        
        user_profile = self.profile_store.read_text(user_id)
        ctx = self.compact_memory.context(thread_id)
        summary = ctx["summary"]
        recent_messages = ctx["messages"]
        
        sys_prompt = "You are a helpful AI assistant. Keep responses concise.\n"
        if user_profile:
            sys_prompt += f"Here are known facts about the user:\n{user_profile}\n"
        if summary:
            sys_prompt += f"Here is a summary of older conversation:\n{summary}\n"
            
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        lc_msgs = [SystemMessage(content=sys_prompt)]
        for m in recent_messages:
            if m["role"] == "user":
                lc_msgs.append(HumanMessage(content=m["content"]))
            else:
                lc_msgs.append(AIMessage(content=m["content"]))
        
        response = self.langchain_agent.invoke(lc_msgs)
        reply_content = str(response.content)
        
        self.compact_memory.append(thread_id, "assistant", reply_content)
        
        agent_cost = estimate_tokens(reply_content)
        if thread_id not in self.thread_tokens:
            self.thread_tokens[thread_id] = 0
        self.thread_tokens[thread_id] += agent_cost
        
        return {"content": reply_content}

    def _maybe_build_langchain_agent(self):
        """Student TODO: wire a live agent with tools and compact middleware."""
        if not self.force_offline:
            self.langchain_agent = build_chat_model(self.config.model)
