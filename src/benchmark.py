from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
from tabulate import tabulate

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    points = 0
    ans_lower = answer.lower()
    for exp in expected:
        if exp.lower() in ans_lower:
            points += 1
    if not expected:
        return 1.0
    return points / len(expected)


def heuristic_quality(answer: str, expected: list[str]) -> float:
    if not answer.strip():
        return 0.0
    return recall_points(answer, expected)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    total_agent_tokens = 0
    total_prompt_tokens = 0
    total_recall = 0.0
    total_quality = 0.0
    compactions = 0
    user_id = "user_bench"
    
    count = 0
    total_questions = 0
    for conv in conversations:
        thread_id = f"thread_{count}"
        count += 1
        
        for turn_content in conv.get("turns", []):
            agent.reply(user_id, thread_id, turn_content)
                
        recall_qs = conv.get("recall_questions", [])
        for rq in recall_qs:
            total_questions += 1
            recall_q = rq.get("question")
            expected_ans = rq.get("expected_contains", [])
            
            if recall_q and expected_ans:
                fresh_thread_id = thread_id + "_recall"
                reply = agent.reply(user_id, fresh_thread_id, recall_q)
                ans = reply.get("content", "")
                
                recall_score = recall_points(ans, expected_ans)
                quality_score = heuristic_quality(ans, expected_ans)
                
                total_recall += recall_score
                total_quality += quality_score
            
        total_agent_tokens += agent.token_usage(thread_id)
        total_prompt_tokens += agent.prompt_token_usage(thread_id)
        compactions += agent.compaction_count(thread_id)
        
    avg_recall = total_recall / max(1, total_questions)
    avg_quality = total_quality / max(1, total_questions)
    mem_size = agent.memory_file_size(user_id) if hasattr(agent, "memory_file_size") else 0
    
    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_quality,
        memory_growth_bytes=mem_size,
        compactions=compactions
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    headers = ["Agent", "Agent Tokens", "Prompt Tokens", "Recall", "Quality", "Memory Growth (B)", "Compactions"]
    data = []
    for r in rows:
        data.append([
            r.agent_name, 
            r.agent_tokens_only, 
            r.prompt_tokens_processed, 
            f"{r.recall_score:.2f}", 
            f"{r.response_quality:.2f}", 
            r.memory_growth_bytes, 
            r.compactions
        ])
    return tabulate(data, headers=headers, tablefmt="github")


def main() -> None:
    config = load_config(Path(__file__).resolve().parent.parent)

    data_dir = config.data_dir
    std_data = load_conversations(data_dir / "conversations.json")
    long_data = load_conversations(data_dir / "advanced_long_context.json")
    
    print("=== Standard Benchmark ===")
    b1 = run_agent_benchmark("Baseline", BaselineAgent(config, force_offline=True), std_data, config)
    a1 = run_agent_benchmark("Advanced", AdvancedAgent(config, force_offline=True), std_data, config)
    print(format_rows([b1, a1]))
    
    print("\n=== Long-Context Stress Benchmark ===")
    b2 = run_agent_benchmark("Baseline", BaselineAgent(config, force_offline=True), long_data, config)
    a2 = run_agent_benchmark("Advanced", AdvancedAgent(config, force_offline=True), long_data, config)
    print(format_rows([b2, a2]))


if __name__ == "__main__":
    main()
