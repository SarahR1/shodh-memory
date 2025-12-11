#!/usr/bin/env python3
"""
LoCoMo-MC10 Benchmark Evaluation for Shodh-Memory

This script evaluates Shodh-Memory on the LoCoMo-MC10 benchmark,
a 1,986-item multiple-choice test for long-term conversational memory.

Supports multiple LLM backends:
  - OpenAI (gpt-4o-mini, gpt-4o)
  - Anthropic (claude-3-haiku, claude-3-sonnet)
  - Ollama (llama3.2, mistral, etc.) - FREE, local
  - Baseten (hosted OSS models) - FREE tier available
  - Any OpenAI-compatible API (Together, Groq, etc.)

Requirements:
    pip install datasets tqdm shodh-memory
    pip install openai  # For OpenAI/compatible APIs
    pip install anthropic  # For Anthropic
    pip install ollama  # For Ollama (local)

Usage:
    # OpenAI
    python locomo_mc10_eval.py --provider openai --model gpt-4o-mini --limit 50

    # Ollama (FREE - local)
    python locomo_mc10_eval.py --provider ollama --model llama3.2 --limit 100

    # Baseten (FREE tier)
    python locomo_mc10_eval.py --provider baseten --model llama-3-8b --limit 100

    # Together.ai (OpenAI-compatible)
    python locomo_mc10_eval.py --provider openai-compatible \\
        --api-base https://api.together.xyz/v1 \\
        --model meta-llama/Llama-3-8b-chat-hf --limit 100

    # Groq (FREE tier, very fast)
    python locomo_mc10_eval.py --provider openai-compatible \\
        --api-base https://api.groq.com/openai/v1 \\
        --model llama-3.1-8b-instant --limit 100
"""

import argparse
import json
import os
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

try:
    from datasets import load_dataset
except ImportError:
    print("Install datasets: pip install datasets")
    exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("Install tqdm: pip install tqdm")
    exit(1)

try:
    from shodh_memory import Memory
except ImportError:
    print("Install shodh-memory: pip install shodh-memory")
    print("Or build locally: maturin develop --release")
    exit(1)


# ============================================================================
# LLM Provider Abstraction
# ============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Generate completion for prompt."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        from openai import OpenAI
        self.model = model
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        return response.choices[0].message.content.strip()


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs (Together, Groq, Baseten, etc.)."""

    def __init__(self, model: str, api_base: str, api_key: Optional[str] = None):
        from openai import OpenAI
        self.model = model
        self.client = OpenAI(
            base_url=api_base,
            api_key=api_key or os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
        )

    def complete(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        return response.choices[0].message.content.strip()


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        from anthropic import Anthropic
        self.model = model
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()


class OllamaProvider(LLMProvider):
    """Ollama local provider - FREE!"""

    def __init__(self, model: str, host: str = "http://localhost:11434"):
        try:
            import ollama
            self.model = model
            self.host = host
        except ImportError:
            print("Install ollama: pip install ollama")
            print("Also ensure Ollama is running: ollama serve")
            exit(1)

    def complete(self, prompt: str) -> str:
        import ollama
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0, "num_predict": 10}
        )
        return response["message"]["content"].strip()


class BasetenProvider(LLMProvider):
    """Baseten hosted models provider."""

    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("BASETEN_API_KEY")
        if not self.api_key:
            print("Set BASETEN_API_KEY environment variable")
            exit(1)

    def complete(self, prompt: str) -> str:
        import requests

        # Baseten model deployment URL format
        url = f"https://model-{self.model}.api.baseten.co/production/predict"

        response = requests.post(
            url,
            headers={"Authorization": f"Api-Key {self.api_key}"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0
            }
        )

        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"].strip()
        elif "output" in result:
            return result["output"].strip()
        else:
            return str(result)


def create_provider(
    provider: str,
    model: str,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None
) -> LLMProvider:
    """Factory function to create LLM provider."""

    if provider == "openai":
        return OpenAIProvider(model, api_key)
    elif provider == "openai-compatible":
        if not api_base:
            raise ValueError("--api-base required for openai-compatible provider")
        return OpenAICompatibleProvider(model, api_base, api_key)
    elif provider == "anthropic":
        return AnthropicProvider(model, api_key)
    elif provider == "ollama":
        return OllamaProvider(model)
    elif provider == "baseten":
        return BasetenProvider(model, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")


@dataclass
class EvalResult:
    question_id: str
    question_type: str
    correct: bool
    predicted_idx: int
    correct_idx: int
    latency_store_ms: float
    latency_recall_ms: float
    num_memories_stored: int


def store_conversations(memory: Memory, sessions: list[str], summaries: list[str]) -> tuple[int, float]:
    """Store conversation sessions into Shodh-Memory."""
    start = time.perf_counter()
    count = 0

    for i, (session, summary) in enumerate(zip(sessions, summaries)):
        # Store the summary as a high-level memory
        if summary and summary.strip():
            memory.remember(
                content=f"Session {i+1} Summary: {summary[:2000]}",  # Truncate long summaries
                memory_type="Context",
                tags=[f"session_{i+1}", "summary"]
            )
            count += 1

        # Store conversation chunks (split long sessions)
        if session and session.strip():
            # Split into chunks of ~500 chars to avoid memory bloat
            chunks = [session[j:j+500] for j in range(0, len(session), 500)]
            for chunk_idx, chunk in enumerate(chunks[:10]):  # Max 10 chunks per session
                memory.remember(
                    content=f"Session {i+1}: {chunk}",
                    memory_type="Conversation",
                    tags=[f"session_{i+1}", "dialogue"]
                )
                count += 1

    elapsed_ms = (time.perf_counter() - start) * 1000
    return count, elapsed_ms


def recall_context(memory: Memory, question: str, limit: int = 5) -> tuple[str, float]:
    """Retrieve relevant context for a question."""
    start = time.perf_counter()

    results = memory.recall(query=question, limit=limit)

    elapsed_ms = (time.perf_counter() - start) * 1000

    if results:
        context = "\n\n".join([f"[Memory {i+1}]: {r.content}" for i, r in enumerate(results)])
    else:
        context = "(No relevant memories found)"

    return context, elapsed_ms


def select_answer_with_llm(
    provider: LLMProvider,
    question: str,
    choices: list[str],
    context: str
) -> int:
    """Use LLM to select the best answer given retrieved context."""

    choices_text = "\n".join([f"{i}. {choice}" for i, choice in enumerate(choices)])

    prompt = f"""Based on the following conversation memories, answer the question by selecting the correct option.

RETRIEVED MEMORIES:
{context}

QUESTION: {question}

OPTIONS:
{choices_text}

Instructions:
- Analyze the memories to find relevant information
- Select the option that best answers the question
- Respond with ONLY the option number (0-9)
- If unsure, make your best guess based on available information

Your answer (single digit 0-9):"""

    try:
        answer_text = provider.complete(prompt)
        # Extract digit from response
        for char in answer_text:
            if char.isdigit():
                idx = int(char)
                if 0 <= idx <= 9:
                    return idx
        return 0  # Default to first option if parsing fails

    except Exception as e:
        print(f"LLM Error: {e}")
        return 0


def evaluate_single_item(
    item: dict,
    provider: LLMProvider,
    db_path: str
) -> EvalResult:
    """Evaluate a single LoCoMo-MC10 item."""

    # Create fresh memory instance for this conversation
    memory = Memory(
        user_id=f"locomo_{item['question_id']}",
        db_path=db_path
    )

    # Store conversation sessions
    sessions = item.get("haystack_sessions", [])
    summaries = item.get("haystack_session_summaries", [])
    num_stored, store_latency = store_conversations(memory, sessions, summaries)

    # Recall relevant context
    context, recall_latency = recall_context(memory, item["question"], limit=5)

    # Select answer using LLM
    predicted_idx = select_answer_with_llm(
        provider=provider,
        question=item["question"],
        choices=item["choices"],
        context=context
    )

    correct_idx = item["correct_choice_index"]
    is_correct = predicted_idx == correct_idx

    return EvalResult(
        question_id=item["question_id"],
        question_type=item["question_type"],
        correct=is_correct,
        predicted_idx=predicted_idx,
        correct_idx=correct_idx,
        latency_store_ms=store_latency,
        latency_recall_ms=recall_latency,
        num_memories_stored=num_stored
    )


def run_evaluation(
    provider_name: str = "openai",
    model: str = "gpt-4o-mini",
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: str = "./locomo_eval_db",
    output_file: str = "locomo_results.json"
):
    """Run the full LoCoMo-MC10 evaluation."""

    print("=" * 60)
    print("LoCoMo-MC10 Benchmark for Shodh-Memory")
    print("=" * 60)

    # Create LLM provider
    print(f"\nInitializing {provider_name} provider with model: {model}")
    provider = create_provider(provider_name, model, api_base, api_key)

    # Load dataset
    print("Loading LoCoMo-MC10 dataset...")
    dataset = load_dataset("Percena/locomo-mc10", split="train")

    total_items = len(dataset)
    if limit:
        dataset = dataset.select(range(min(limit, total_items)))

    print(f"Evaluating {len(dataset)} / {total_items} items")
    print(f"Provider: {provider_name}")
    print(f"Model: {model}")
    print(f"DB Path: {db_path}")
    print()

    # Run evaluation
    results: list[EvalResult] = []

    for item in tqdm(dataset, desc="Evaluating"):
        result = evaluate_single_item(
            item=item,
            provider=provider,
            db_path=db_path
        )
        results.append(result)

    # Calculate metrics
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    # Overall accuracy
    total_correct = sum(1 for r in results if r.correct)
    overall_accuracy = total_correct / len(results) * 100

    print(f"\nOverall Accuracy: {overall_accuracy:.2f}% ({total_correct}/{len(results)})")

    # Per-category accuracy
    by_type = defaultdict(list)
    for r in results:
        by_type[r.question_type].append(r.correct)

    print("\nAccuracy by Question Type:")
    print("-" * 40)
    for qtype, correct_list in sorted(by_type.items()):
        acc = sum(correct_list) / len(correct_list) * 100
        print(f"  {qtype:20s}: {acc:6.2f}% ({sum(correct_list)}/{len(correct_list)})")

    # Latency stats
    avg_store = sum(r.latency_store_ms for r in results) / len(results)
    avg_recall = sum(r.latency_recall_ms for r in results) / len(results)
    avg_memories = sum(r.num_memories_stored for r in results) / len(results)

    print(f"\nLatency (avg):")
    print(f"  Store:  {avg_store:.1f} ms")
    print(f"  Recall: {avg_recall:.1f} ms")
    print(f"  Memories stored per conversation: {avg_memories:.1f}")

    # Save detailed results
    output_data = {
        "provider": provider_name,
        "model": model,
        "total_items": len(results),
        "overall_accuracy": overall_accuracy,
        "accuracy_by_type": {
            qtype: sum(correct_list) / len(correct_list) * 100
            for qtype, correct_list in by_type.items()
        },
        "latency_store_ms_avg": avg_store,
        "latency_recall_ms_avg": avg_recall,
        "results": [
            {
                "question_id": r.question_id,
                "question_type": r.question_type,
                "correct": r.correct,
                "predicted_idx": r.predicted_idx,
                "correct_idx": r.correct_idx,
                "latency_store_ms": r.latency_store_ms,
                "latency_recall_ms": r.latency_recall_ms
            }
            for r in results
        ]
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    # Random baseline
    print(f"\nRandom baseline (10 choices): 10.00%")
    print(f"Improvement over random: {overall_accuracy - 10:.2f}%")

    return output_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LoCoMo-MC10 Benchmark for Shodh-Memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # OpenAI (requires OPENAI_API_KEY)
  python locomo_mc10_eval.py --provider openai --model gpt-4o-mini --limit 50

  # Baseten (OpenAI-compatible, uses your API key)
  python locomo_mc10_eval.py --provider openai-compatible \\
      --api-base https://inference.baseten.co/v1 \\
      --api-key YOUR_KEY --model openai/gpt-oss-120b --limit 100

  # Groq (FREE tier, very fast)
  python locomo_mc10_eval.py --provider openai-compatible \\
      --api-base https://api.groq.com/openai/v1 \\
      --model llama-3.1-8b-instant --limit 100

  # Ollama (FREE - local)
  python locomo_mc10_eval.py --provider ollama --model llama3.2 --limit 100
        """
    )
    parser.add_argument("--provider", default="openai",
                        choices=["openai", "openai-compatible", "anthropic", "ollama", "baseten"],
                        help="LLM provider to use")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model name")
    parser.add_argument("--api-base", default=None, help="API base URL (required for openai-compatible)")
    parser.add_argument("--api-key", default=None, help="API key (or use env vars: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items (for testing)")
    parser.add_argument("--db-path", default="./locomo_eval_db", help="Path for Shodh-Memory database")
    parser.add_argument("--output", default="locomo_results.json", help="Output file for results")
    parser.add_argument("--full", action="store_true", help="Run full evaluation (all 1986 items)")

    args = parser.parse_args()

    limit = None if args.full else (args.limit or 50)  # Default to 50 for quick test

    run_evaluation(
        provider_name=args.provider,
        model=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
        limit=limit,
        db_path=args.db_path,
        output_file=args.output
    )
