from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


def make_config(tmp_path: Path):
    config = load_config()
    config.state_dir = tmp_path / "state"
    config.compact_threshold_tokens = 50
    config.compact_keep_messages = 2
    return config


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    from memory_store import UserProfileStore
    store = UserProfileStore(tmp_path)
    store.write_text("user1", "name: Quan\n")
    assert "Quan" in store.read_text("user1")
    store.edit_text("user1", "Quan", "Binh")
    assert "Binh" in store.read_text("user1")
    assert store.file_size("user1") > 0


def test_compact_trigger(tmp_path: Path) -> None:
    from memory_store import CompactMemoryManager
    mgr = CompactMemoryManager(threshold_tokens=20, keep_messages=1)
    mgr.append("t1", "user", "Hello this is a very long message to trigger compaction indeed yes it is.")
    mgr.append("t1", "assistant", "Yes I see.")
    mgr.append("t1", "user", "Another message.")
    assert mgr.compaction_count("t1") > 0


def test_cross_session_recall(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config=config, force_offline=True)
    baseline = BaselineAgent(config=config, force_offline=True)
    
    advanced.reply("u1", "t1", "Tên tôi là An.")
    baseline.reply("u1", "t1", "Tên tôi là An.")
    
    adv_reply = advanced.reply("u1", "t2", "Tên mình là gì?")
    base_reply = baseline.reply("u1", "t2", "Tên mình là gì?")
    
    assert "An" in adv_reply["content"]
    assert "An" not in base_reply["content"]


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.compact_threshold_tokens = 20
    config.compact_keep_messages = 1
    advanced = AdvancedAgent(config=config, force_offline=True)
    baseline = BaselineAgent(config=config, force_offline=True)
    
    for i in range(10):
        advanced.reply("u1", "t1", f"Message {i} with some extra length to trigger things.")
        baseline.reply("u1", "t1", f"Message {i} with some extra length to trigger things.")
        
    assert advanced.prompt_token_usage("t1") < baseline.prompt_token_usage("t1")
