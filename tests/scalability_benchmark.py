#!/usr/bin/env python3
"""
Scalability Benchmark: Tests performance at different memory counts (50, 100, 1000)
Standard benchmark for measuring how operations scale with data size.
"""

import json
import os
import sys
import time
import tempfile
import shutil
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

import requests

try:
    from shodh_memory import Memory
    NATIVE_AVAILABLE = True
except ImportError:
    Memory = None  # Define as None for type hints
    NATIVE_AVAILABLE = False
    print("WARNING: Native shodh_memory not available")

REST_BASE_URL = os.environ.get("SHODH_REST_URL", "http://127.0.0.1:3030")  # IPv4 to avoid Windows IPv6 delay
API_KEY = os.environ.get("SHODH_API_KEY", "sk-shodh-dev-4f8b2c1d9e3a7f5b6d2c8e4a1b9f7d3c")

SCALE_POINTS = [50, 100, 1000]
QUERY_ITERATIONS = 10


@dataclass
class ScaleResult:
    """Results for a single scale point"""
    memory_count: int
    # Insert metrics (total time to insert all memories)
    native_insert_total_ms: float = 0.0
    rest_insert_total_ms: float = 0.0
    native_insert_avg_ms: float = 0.0
    rest_insert_avg_ms: float = 0.0
    # Recall (semantic search) metrics
    native_recall_avg_ms: float = 0.0
    rest_recall_avg_ms: float = 0.0
    native_recall_p99_ms: float = 0.0
    rest_recall_p99_ms: float = 0.0
    # List metrics
    native_list_avg_ms: float = 0.0
    rest_list_avg_ms: float = 0.0
    # Context summary metrics
    native_context_avg_ms: float = 0.0
    rest_context_avg_ms: float = 0.0
    # Stats metrics
    native_stats_avg_ms: float = 0.0
    rest_stats_avg_ms: float = 0.0
    # Success flags
    native_success: bool = True
    rest_success: bool = True
    native_error: str = ""
    rest_error: str = ""


class RESTClient:
    """Minimal REST client for benchmarking"""

    def __init__(self, base_url: str, api_key: str, user_id: str):
        self.base_url = base_url
        self.api_key = api_key
        self.user_id = user_id
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": api_key
        })

    def remember(self, content: str, memory_type: str = "Observation", tags: List[str] = None) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/remember", json={
            "user_id": self.user_id,
            "content": content,
            "memory_type": memory_type,
            "tags": tags or []
        })
        resp.raise_for_status()
        return resp.json()

    def recall(self, query: str, limit: int = 10) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/recall", json={
            "user_id": self.user_id,
            "query": query,
            "limit": limit
        })
        resp.raise_for_status()
        return resp.json()

    def list_memories(self, limit: int = 100) -> Dict:
        resp = self.session.get(f"{self.base_url}/api/list/{self.user_id}", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()

    def context_summary(self, max_items: int = 5) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/context_summary", json={
            "user_id": self.user_id,
            "max_items": max_items,
            "include_decisions": True,
            "include_learnings": True,
            "include_context": True
        })
        resp.raise_for_status()
        return resp.json()

    def get_stats(self) -> Dict:
        resp = self.session.get(f"{self.base_url}/api/users/{self.user_id}/stats")
        resp.raise_for_status()
        return resp.json()


def generate_realistic_content(index: int) -> Tuple[str, str, List[str]]:
    """Generate realistic memory content for benchmarking"""
    templates = [
        ("User prefers {adj} mode for {feature}", "Decision", ["preference", "ui"]),
        ("API endpoint {action} to {endpoint}", "Context", ["api", "architecture"]),
        ("Database {operation} completed in {duration}ms", "Discovery", ["database", "performance"]),
        ("{framework} version updated to {version}", "Learning", ["dependency", "update"]),
        ("Error rate {direction} after {change}", "Pattern", ["monitoring", "ops"]),
        ("Cache hit ratio is {percentage}%", "Observation", ["cache", "performance"]),
        ("Authentication tokens expire after {duration}", "Learning", ["auth", "security"]),
        ("Load balancer {status} for {service}", "Context", ["infrastructure", "ops"]),
        ("Memory usage {direction} by {amount}MB", "Discovery", ["memory", "performance"]),
        ("Test coverage reached {percentage}%", "Learning", ["testing", "quality"]),
    ]

    template, mem_type, base_tags = random.choice(templates)

    replacements = {
        "adj": random.choice(["dark", "light", "compact", "expanded"]),
        "feature": random.choice(["better visibility", "accessibility", "performance", "usability"]),
        "action": random.choice(["changed", "migrated", "updated", "deprecated"]),
        "endpoint": random.choice(["/v2/auth", "/api/users", "/graphql", "/health"]),
        "operation": random.choice(["migration", "backup", "optimization", "replication"]),
        "duration": str(random.randint(50, 500)),
        "framework": random.choice(["React", "Vue", "Angular", "Svelte"]),
        "version": f"{random.randint(1, 5)}.{random.randint(0, 20)}.{random.randint(0, 10)}",
        "direction": random.choice(["increased", "decreased", "stabilized"]),
        "change": random.choice(["deployment", "refactor", "config update"]),
        "percentage": str(random.randint(70, 99)),
        "status": random.choice(["healthy", "degraded", "recovering"]),
        "service": random.choice(["api-gateway", "auth-service", "data-processor"]),
        "amount": str(random.randint(50, 500)),
    }

    content = template
    for key, value in replacements.items():
        content = content.replace(f"{{{key}}}", value)

    # Add unique identifier
    content = f"[{index}] {content}"
    tags = base_tags + [f"batch-{index // 50}"]

    return content, mem_type, tags


def generate_queries() -> List[str]:
    """Generate realistic search queries"""
    return [
        "user preferences",
        "API changes",
        "database performance",
        "authentication",
        "error monitoring",
        "cache optimization",
        "memory usage",
        "test coverage",
        "infrastructure status",
        "framework updates",
    ]


def percentile(values: List[float], p: float) -> float:
    """Calculate percentile"""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_values) else f
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def check_rest_server() -> bool:
    try:
        resp = requests.get(f"{REST_BASE_URL}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def run_scale_benchmark(memory_count: int, native_mem: Optional[Memory],
                        rest_client: Optional[RESTClient]) -> ScaleResult:
    """Run benchmark at a specific scale point"""
    result = ScaleResult(memory_count=memory_count)
    queries = generate_queries()

    print(f"\n  Populating {memory_count} memories...")

    # =========================================================================
    # 1. INSERT BENCHMARK
    # =========================================================================
    if native_mem:
        native_insert_times = []
        try:
            for i in range(memory_count):
                content, mem_type, tags = generate_realistic_content(i)
                start = time.perf_counter()
                native_mem.remember(content, memory_type=mem_type, tags=tags)
                native_insert_times.append((time.perf_counter() - start) * 1000)

                if (i + 1) % 100 == 0:
                    print(f"    Native: {i + 1}/{memory_count} inserted...")

            result.native_insert_total_ms = sum(native_insert_times)
            result.native_insert_avg_ms = result.native_insert_total_ms / memory_count
            print(f"    Native insert: {result.native_insert_total_ms:.0f}ms total, "
                  f"{result.native_insert_avg_ms:.2f}ms/item")
        except Exception as e:
            result.native_success = False
            result.native_error = str(e)
            print(f"    Native insert FAILED: {e}")

    if rest_client:
        rest_insert_times = []
        try:
            for i in range(memory_count):
                content, mem_type, tags = generate_realistic_content(i + memory_count)  # Different content
                start = time.perf_counter()
                rest_client.remember(content, memory_type=mem_type, tags=tags)
                rest_insert_times.append((time.perf_counter() - start) * 1000)

                if (i + 1) % 100 == 0:
                    print(f"    REST: {i + 1}/{memory_count} inserted...")

            result.rest_insert_total_ms = sum(rest_insert_times)
            result.rest_insert_avg_ms = result.rest_insert_total_ms / memory_count
            print(f"    REST insert: {result.rest_insert_total_ms:.0f}ms total, "
                  f"{result.rest_insert_avg_ms:.2f}ms/item")
        except Exception as e:
            result.rest_success = False
            result.rest_error = str(e)
            print(f"    REST insert FAILED: {e}")

    print(f"  Running queries ({QUERY_ITERATIONS} iterations per query)...")

    # =========================================================================
    # 2. RECALL (SEMANTIC SEARCH) BENCHMARK
    # =========================================================================
    if native_mem and result.native_success:
        native_recall_times = []
        try:
            for query in queries:
                for _ in range(QUERY_ITERATIONS):
                    start = time.perf_counter()
                    native_mem.recall(query, limit=10)
                    native_recall_times.append((time.perf_counter() - start) * 1000)

            result.native_recall_avg_ms = sum(native_recall_times) / len(native_recall_times)
            result.native_recall_p99_ms = percentile(native_recall_times, 99)
        except Exception as e:
            result.native_success = False
            result.native_error = str(e)

    if rest_client and result.rest_success:
        rest_recall_times = []
        try:
            for query in queries:
                for _ in range(QUERY_ITERATIONS):
                    start = time.perf_counter()
                    rest_client.recall(query, limit=10)
                    rest_recall_times.append((time.perf_counter() - start) * 1000)

            result.rest_recall_avg_ms = sum(rest_recall_times) / len(rest_recall_times)
            result.rest_recall_p99_ms = percentile(rest_recall_times, 99)
        except Exception as e:
            result.rest_success = False
            result.rest_error = str(e)

    # =========================================================================
    # 3. LIST BENCHMARK
    # =========================================================================
    if native_mem and result.native_success:
        native_list_times = []
        try:
            for _ in range(QUERY_ITERATIONS):
                start = time.perf_counter()
                native_mem.list_memories(limit=100)
                native_list_times.append((time.perf_counter() - start) * 1000)
            result.native_list_avg_ms = sum(native_list_times) / len(native_list_times)
        except Exception as e:
            result.native_success = False
            result.native_error = str(e)

    if rest_client and result.rest_success:
        rest_list_times = []
        try:
            for _ in range(QUERY_ITERATIONS):
                start = time.perf_counter()
                rest_client.list_memories(limit=100)
                rest_list_times.append((time.perf_counter() - start) * 1000)
            result.rest_list_avg_ms = sum(rest_list_times) / len(rest_list_times)
        except Exception as e:
            result.rest_success = False
            result.rest_error = str(e)

    # =========================================================================
    # 4. CONTEXT SUMMARY BENCHMARK
    # =========================================================================
    if native_mem and result.native_success:
        native_context_times = []
        try:
            for _ in range(QUERY_ITERATIONS):
                start = time.perf_counter()
                native_mem.context_summary(max_items=5)
                native_context_times.append((time.perf_counter() - start) * 1000)
            result.native_context_avg_ms = sum(native_context_times) / len(native_context_times)
        except Exception as e:
            result.native_success = False
            result.native_error = str(e)

    if rest_client and result.rest_success:
        rest_context_times = []
        try:
            for _ in range(QUERY_ITERATIONS):
                start = time.perf_counter()
                rest_client.context_summary(max_items=5)
                rest_context_times.append((time.perf_counter() - start) * 1000)
            result.rest_context_avg_ms = sum(rest_context_times) / len(rest_context_times)
        except Exception as e:
            result.rest_success = False
            result.rest_error = str(e)

    # =========================================================================
    # 5. STATS BENCHMARK
    # =========================================================================
    if native_mem and result.native_success:
        native_stats_times = []
        try:
            for _ in range(QUERY_ITERATIONS):
                start = time.perf_counter()
                native_mem.get_stats()
                native_stats_times.append((time.perf_counter() - start) * 1000)
            result.native_stats_avg_ms = sum(native_stats_times) / len(native_stats_times)
        except Exception as e:
            result.native_success = False
            result.native_error = str(e)

    if rest_client and result.rest_success:
        rest_stats_times = []
        try:
            for _ in range(QUERY_ITERATIONS):
                start = time.perf_counter()
                rest_client.get_stats()
                rest_stats_times.append((time.perf_counter() - start) * 1000)
            result.rest_stats_avg_ms = sum(rest_stats_times) / len(rest_stats_times)
        except Exception as e:
            result.rest_success = False
            result.rest_error = str(e)

    return result


def run_benchmarks() -> List[ScaleResult]:
    """Run benchmarks at all scale points"""
    results: List[ScaleResult] = []

    rest_available = check_rest_server()

    print("=" * 80)
    print("SHODH-MEMORY SCALABILITY BENCHMARK")
    print("=" * 80)
    print(f"Native Python available: {NATIVE_AVAILABLE}")
    print(f"REST Server available:   {rest_available} ({REST_BASE_URL})")
    print(f"Scale points:            {SCALE_POINTS}")
    print(f"Query iterations:        {QUERY_ITERATIONS}")
    print("=" * 80)

    if not NATIVE_AVAILABLE and not rest_available:
        print("ERROR: Neither native nor REST API is available!")
        return results

    for scale in SCALE_POINTS:
        print(f"\n{'='*80}")
        print(f"SCALE POINT: {scale} memories")
        print(f"{'='*80}")

        # Create fresh instances for each scale point
        temp_dir = tempfile.mkdtemp(prefix=f"shodh_scale_{scale}_")
        native_mem = None
        rest_client = None

        try:
            if NATIVE_AVAILABLE:
                native_mem = Memory(storage_path=temp_dir)

            if rest_available:
                # Use unique user ID per scale to avoid cross-contamination
                rest_client = RESTClient(REST_BASE_URL, API_KEY, f"scale-test-{scale}")

            result = run_scale_benchmark(scale, native_mem, rest_client)
            results.append(result)

        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    return results


def print_results(results: List[ScaleResult]):
    """Print benchmark results in tabular format"""
    print("\n")
    print("=" * 120)
    print("SCALABILITY BENCHMARK RESULTS")
    print("=" * 120)

    # Insert performance table
    print("\n--- INSERT PERFORMANCE ---")
    print(f"{'Scale':<10} {'Native Total':<15} {'Native Avg':<15} {'REST Total':<15} {'REST Avg':<15} {'Speedup':<10}")
    print("-" * 80)
    for r in results:
        native_total = f"{r.native_insert_total_ms:.0f}ms" if r.native_success else "FAILED"
        native_avg = f"{r.native_insert_avg_ms:.2f}ms" if r.native_success else "N/A"
        rest_total = f"{r.rest_insert_total_ms:.0f}ms" if r.rest_success else "FAILED"
        rest_avg = f"{r.rest_insert_avg_ms:.2f}ms" if r.rest_success else "N/A"

        speedup = "N/A"
        if r.native_success and r.rest_success and r.native_insert_avg_ms > 0:
            speedup = f"{r.rest_insert_avg_ms / r.native_insert_avg_ms:.2f}x"

        print(f"{r.memory_count:<10} {native_total:<15} {native_avg:<15} {rest_total:<15} {rest_avg:<15} {speedup:<10}")

    # Recall (semantic search) performance table
    print("\n--- RECALL (Semantic Search) PERFORMANCE ---")
    print(f"{'Scale':<10} {'Native Avg':<15} {'Native P99':<15} {'REST Avg':<15} {'REST P99':<15} {'Speedup':<10}")
    print("-" * 80)
    for r in results:
        native_avg = f"{r.native_recall_avg_ms:.2f}ms" if r.native_success else "FAILED"
        native_p99 = f"{r.native_recall_p99_ms:.2f}ms" if r.native_success else "N/A"
        rest_avg = f"{r.rest_recall_avg_ms:.2f}ms" if r.rest_success else "FAILED"
        rest_p99 = f"{r.rest_recall_p99_ms:.2f}ms" if r.rest_success else "N/A"

        speedup = "N/A"
        if r.native_success and r.rest_success and r.native_recall_avg_ms > 0:
            speedup = f"{r.rest_recall_avg_ms / r.native_recall_avg_ms:.2f}x"

        print(f"{r.memory_count:<10} {native_avg:<15} {native_p99:<15} {rest_avg:<15} {rest_p99:<15} {speedup:<10}")

    # List performance table
    print("\n--- LIST MEMORIES PERFORMANCE ---")
    print(f"{'Scale':<10} {'Native Avg':<15} {'REST Avg':<15} {'Speedup':<10}")
    print("-" * 50)
    for r in results:
        native_avg = f"{r.native_list_avg_ms:.2f}ms" if r.native_success else "FAILED"
        rest_avg = f"{r.rest_list_avg_ms:.2f}ms" if r.rest_success else "FAILED"

        speedup = "N/A"
        if r.native_success and r.rest_success and r.native_list_avg_ms > 0:
            speedup = f"{r.rest_list_avg_ms / r.native_list_avg_ms:.2f}x"

        print(f"{r.memory_count:<10} {native_avg:<15} {rest_avg:<15} {speedup:<10}")

    # Context summary performance table
    print("\n--- CONTEXT SUMMARY PERFORMANCE ---")
    print(f"{'Scale':<10} {'Native Avg':<15} {'REST Avg':<15} {'Speedup':<10}")
    print("-" * 50)
    for r in results:
        native_avg = f"{r.native_context_avg_ms:.2f}ms" if r.native_success else "FAILED"
        rest_avg = f"{r.rest_context_avg_ms:.2f}ms" if r.rest_success else "FAILED"

        speedup = "N/A"
        if r.native_success and r.rest_success and r.native_context_avg_ms > 0:
            speedup = f"{r.rest_context_avg_ms / r.native_context_avg_ms:.2f}x"

        print(f"{r.memory_count:<10} {native_avg:<15} {rest_avg:<15} {speedup:<10}")

    # Stats performance table
    print("\n--- GET STATS PERFORMANCE ---")
    print(f"{'Scale':<10} {'Native Avg':<15} {'REST Avg':<15} {'Speedup':<10}")
    print("-" * 50)
    for r in results:
        native_avg = f"{r.native_stats_avg_ms:.2f}ms" if r.native_success else "FAILED"
        rest_avg = f"{r.rest_stats_avg_ms:.2f}ms" if r.rest_success else "FAILED"

        speedup = "N/A"
        if r.native_success and r.rest_success and r.native_stats_avg_ms > 0:
            speedup = f"{r.rest_stats_avg_ms / r.native_stats_avg_ms:.2f}x"

        print(f"{r.memory_count:<10} {native_avg:<15} {rest_avg:<15} {speedup:<10}")

    print("\n" + "=" * 120)
    print("SCALING ANALYSIS")
    print("=" * 120)

    # Calculate scaling factors
    if len(results) >= 2:
        base = results[0]
        for i, r in enumerate(results[1:], 1):
            scale_factor = r.memory_count / base.memory_count

            print(f"\n{base.memory_count} -> {r.memory_count} memories ({scale_factor}x data):")

            if base.native_recall_avg_ms > 0 and r.native_recall_avg_ms > 0:
                native_scaling = r.native_recall_avg_ms / base.native_recall_avg_ms
                print(f"  Native recall: {native_scaling:.2f}x slower ({base.native_recall_avg_ms:.2f}ms -> {r.native_recall_avg_ms:.2f}ms)")

            if base.rest_recall_avg_ms > 0 and r.rest_recall_avg_ms > 0:
                rest_scaling = r.rest_recall_avg_ms / base.rest_recall_avg_ms
                print(f"  REST recall:   {rest_scaling:.2f}x slower ({base.rest_recall_avg_ms:.2f}ms -> {r.rest_recall_avg_ms:.2f}ms)")

    print("\n" + "=" * 120)
    print("Notes:")
    print("- Speedup = REST time / Native time (higher = native is faster)")
    print("- P99 = 99th percentile latency")
    print("- Scaling factor < data growth factor indicates sublinear scaling (good)")
    print("=" * 120)


def main():
    results = run_benchmarks()
    print_results(results)

    all_success = all(r.native_success and r.rest_success for r in results)
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
