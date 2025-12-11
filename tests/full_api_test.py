#!/usr/bin/env python3
"""
Comprehensive API Test Suite: Tests all REST endpoints and Native Python API
This script tests every endpoint for both correctness and timing.
"""

import json
import os
import sys
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import requests

# Try to import native bindings
try:
    from shodh_memory import Memory
    NATIVE_AVAILABLE = True
except ImportError:
    NATIVE_AVAILABLE = False
    print("WARNING: Native shodh_memory not available. Install with: maturin develop --release")

# Configuration
REST_BASE_URL = os.environ.get("SHODH_REST_URL", "http://127.0.0.1:3030")  # IPv4 to avoid Windows IPv6 delay
API_KEY = os.environ.get("SHODH_API_KEY", "sk-shodh-dev-4f8b2c1d9e3a7f5b6d2c8e4a1b9f7d3c")
USER_ID = "full-test-user"


class TestResult:
    def __init__(self, name: str, endpoint: str):
        self.name = name
        self.endpoint = endpoint
        self.native_time_ms: Optional[float] = None
        self.rest_time_ms: Optional[float] = None
        self.native_success = True
        self.rest_success = True
        self.native_error: Optional[str] = None
        self.rest_error: Optional[str] = None
        self.native_result: Any = None
        self.rest_result: Any = None


def time_operation(func, *args, **kwargs) -> Tuple[float, Any]:
    """Time a single operation and return (elapsed_ms, result)"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed, result


class RESTClient:
    """Complete REST client for all shodh-memory API endpoints"""

    def __init__(self, base_url: str, api_key: str, user_id: str):
        self.base_url = base_url
        self.api_key = api_key
        self.user_id = user_id
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": api_key
        })

    # Core Memory Operations
    def remember(self, content: str, memory_type: str = "Observation",
                 tags: List[str] = None, metadata: Dict = None) -> Dict:
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

    def recall_by_tags(self, tags: List[str], limit: int = 10) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/recall/tags", json={
            "user_id": self.user_id,
            "tags": tags,
            "limit": limit
        })
        resp.raise_for_status()
        return resp.json()

    def recall_by_date(self, start: str, end: str, limit: int = 10) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/recall/date", json={
            "user_id": self.user_id,
            "start": start,
            "end": end,
            "limit": limit
        })
        resp.raise_for_status()
        return resp.json()

    def list_memories(self, limit: int = 100) -> Dict:
        resp = self.session.get(f"{self.base_url}/api/list/{self.user_id}",
                               params={"limit": limit})
        resp.raise_for_status()
        return resp.json()

    def get_memory(self, memory_id: str) -> Dict:
        resp = self.session.get(f"{self.base_url}/api/memory/{memory_id}",
                               params={"user_id": self.user_id})
        resp.raise_for_status()
        return resp.json()

    def update_memory(self, memory_id: str, content: str) -> Dict:
        resp = self.session.put(f"{self.base_url}/api/memory/{memory_id}", json={
            "user_id": self.user_id,
            "content": content
        })
        resp.raise_for_status()
        return resp.json()

    def forget(self, memory_id: str) -> Dict:
        resp = self.session.delete(f"{self.base_url}/api/memory/{memory_id}",
                                   params={"user_id": self.user_id})
        resp.raise_for_status()
        return resp.json()

    # Forget Operations
    def forget_by_tags(self, tags: List[str]) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/forget/tags", json={
            "user_id": self.user_id,
            "tags": tags
        })
        resp.raise_for_status()
        return resp.json()

    def forget_by_age(self, days: int) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/forget/age", json={
            "user_id": self.user_id,
            "days_old": days
        })
        resp.raise_for_status()
        return resp.json()

    def forget_by_importance(self, threshold: float) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/forget/importance", json={
            "user_id": self.user_id,
            "threshold": threshold
        })
        resp.raise_for_status()
        return resp.json()

    def forget_by_pattern(self, pattern: str) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/forget/pattern", json={
            "user_id": self.user_id,
            "pattern": pattern
        })
        resp.raise_for_status()
        return resp.json()

    def forget_by_date(self, start: str, end: str) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/forget/date", json={
            "user_id": self.user_id,
            "start": start,
            "end": end
        })
        resp.raise_for_status()
        return resp.json()

    # Context & Introspection
    def context_summary(self, max_items: int = 5, include_decisions: bool = True,
                       include_learnings: bool = True, include_context: bool = True) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/context_summary", json={
            "user_id": self.user_id,
            "max_items": max_items,
            "include_decisions": include_decisions,
            "include_learnings": include_learnings,
            "include_context": include_context
        })
        resp.raise_for_status()
        return resp.json()

    def brain_state(self) -> Dict:
        resp = self.session.get(f"{self.base_url}/api/brain/{self.user_id}")
        resp.raise_for_status()
        return resp.json()

    def get_stats(self) -> Dict:
        resp = self.session.get(f"{self.base_url}/api/users/{self.user_id}/stats")
        resp.raise_for_status()
        return resp.json()

    def graph_stats(self) -> Dict:
        resp = self.session.get(f"{self.base_url}/api/graph/{self.user_id}/stats")
        resp.raise_for_status()
        return resp.json()

    # Batch Operations
    def batch_remember(self, memories: List[Dict]) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/batch_remember", json={
            "user_id": self.user_id,
            "memories": memories
        })
        resp.raise_for_status()
        return resp.json()

    # Hebbian Learning
    def retrieve_tracked(self, query: str, limit: int = 5) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/retrieve/tracked", json={
            "user_id": self.user_id,
            "query": query,
            "limit": limit
        })
        resp.raise_for_status()
        return resp.json()

    def reinforce(self, memory_ids: List[str], outcome: str = "helpful") -> Dict:
        resp = self.session.post(f"{self.base_url}/api/reinforce", json={
            "user_id": self.user_id,
            "memory_ids": memory_ids,
            "outcome": outcome
        })
        resp.raise_for_status()
        return resp.json()

    # Consolidation
    def consolidate(self) -> Dict:
        resp = self.session.post(f"{self.base_url}/api/consolidate", json={
            "user_id": self.user_id
        })
        resp.raise_for_status()
        return resp.json()

    # Advanced Search
    def advanced_search(self, query: str, filters: Dict = None) -> Dict:
        payload = {
            "user_id": self.user_id,
            "query": query,
            "limit": 10
        }
        if filters:
            payload.update(filters)
        resp = self.session.post(f"{self.base_url}/api/search/advanced", json=payload)
        resp.raise_for_status()
        return resp.json()

    # Health & Metrics
    def health(self) -> Dict:
        resp = self.session.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def health_live(self) -> Dict:
        resp = self.session.get(f"{self.base_url}/health/live")
        resp.raise_for_status()
        return resp.json()

    def health_ready(self) -> Dict:
        resp = self.session.get(f"{self.base_url}/health/ready")
        resp.raise_for_status()
        return resp.json()

    def metrics(self) -> str:
        resp = self.session.get(f"{self.base_url}/metrics")
        resp.raise_for_status()
        return resp.text


def check_rest_server() -> bool:
    """Check if REST server is available"""
    try:
        resp = requests.get(f"{REST_BASE_URL}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def run_tests():
    """Run all API tests"""
    results: List[TestResult] = []

    rest_available = check_rest_server()

    print("=" * 80)
    print("SHODH-MEMORY COMPREHENSIVE API TEST")
    print("=" * 80)
    print(f"Native Python available: {NATIVE_AVAILABLE}")
    print(f"REST Server available:   {rest_available} ({REST_BASE_URL})")
    print("=" * 80)

    if not NATIVE_AVAILABLE and not rest_available:
        print("ERROR: Neither native nor REST API is available!")
        return results

    # Setup
    temp_dir = tempfile.mkdtemp(prefix="shodh_test_")
    native_mem = None
    rest_client = None
    stored_memory_ids: List[str] = []

    try:
        if NATIVE_AVAILABLE:
            native_mem = Memory(storage_path=temp_dir)

        if rest_available:
            rest_client = RESTClient(REST_BASE_URL, API_KEY, USER_ID)

        # =====================================================================
        # 1. Health Endpoints (REST only)
        # =====================================================================
        if rest_client:
            print("\n--- Health Endpoints (REST only) ---")

            # /health
            result = TestResult("health", "GET /health")
            try:
                result.rest_time_ms, result.rest_result = time_operation(rest_client.health)
                print(f"  /health: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  /health: FAILED - {e}")
            results.append(result)

            # /health/live
            result = TestResult("health_live", "GET /health/live")
            try:
                result.rest_time_ms, result.rest_result = time_operation(rest_client.health_live)
                print(f"  /health/live: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  /health/live: FAILED - {e}")
            results.append(result)

            # /health/ready
            result = TestResult("health_ready", "GET /health/ready")
            try:
                result.rest_time_ms, result.rest_result = time_operation(rest_client.health_ready)
                print(f"  /health/ready: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  /health/ready: FAILED - {e}")
            results.append(result)

            # /metrics
            result = TestResult("metrics", "GET /metrics")
            try:
                result.rest_time_ms, result.rest_result = time_operation(rest_client.metrics)
                print(f"  /metrics: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  /metrics: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 2. Remember (Store Memory)
        # =====================================================================
        print("\n--- Remember (Store Memory) ---")
        result = TestResult("remember", "POST /api/remember")

        test_content = "User prefers dark mode for better visibility at night"
        test_tags = ["preference", "ui", "test"]

        if native_mem:
            try:
                result.native_time_ms, native_result = time_operation(
                    native_mem.remember,
                    test_content,
                    memory_type="Decision",
                    tags=test_tags
                )
                result.native_result = native_result
                if native_result and "id" in native_result:
                    stored_memory_ids.append(native_result["id"])
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, rest_result = time_operation(
                    rest_client.remember,
                    test_content,
                    memory_type="Decision",
                    tags=test_tags
                )
                result.rest_result = rest_result
                if rest_result and "id" in rest_result:
                    stored_memory_ids.append(rest_result["id"])
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # Store more memories for later tests
        more_memories = [
            ("JWT tokens expire after 24 hours", "Learning", ["auth", "security"]),
            ("Database migrations should run before app startup", "Decision", ["database", "ops"]),
            ("Performance optimization reduced latency by 40%", "Discovery", ["performance"]),
            ("API endpoint changed to /v2/auth", "Context", ["api", "auth"]),
        ]

        for content, mem_type, tags in more_memories:
            if native_mem:
                try:
                    res = native_mem.remember(content, memory_type=mem_type, tags=tags)
                    if res and "id" in res:
                        stored_memory_ids.append(res["id"])
                except:
                    pass
            if rest_client:
                try:
                    res = rest_client.remember(content, memory_type=mem_type, tags=tags)
                    if res and "id" in res:
                        stored_memory_ids.append(res["id"])
                except:
                    pass

        # =====================================================================
        # 3. Recall (Semantic Search)
        # =====================================================================
        print("\n--- Recall (Semantic Search) ---")
        result = TestResult("recall", "POST /api/recall")

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.recall, "user preferences", limit=5
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.recall, "user preferences", limit=5
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 4. Recall by Tags
        # =====================================================================
        print("\n--- Recall by Tags ---")
        result = TestResult("recall_by_tags", "POST /api/recall/tags")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.recall_by_tags, ["auth"], limit=5
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 5. Recall by Date
        # =====================================================================
        print("\n--- Recall by Date ---")
        result = TestResult("recall_by_date", "POST /api/recall/date")

        now = datetime.utcnow()
        start = (now - timedelta(days=1)).isoformat() + "Z"
        end = (now + timedelta(days=1)).isoformat() + "Z"

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.recall_by_date, start, end, limit=10
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 6. List Memories
        # =====================================================================
        print("\n--- List Memories ---")
        result = TestResult("list_memories", "GET /api/list/{user_id}")

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.list_memories, limit=50
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.list_memories, limit=50
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 7. Get Memory by ID
        # =====================================================================
        if stored_memory_ids:
            print("\n--- Get Memory by ID ---")
            result = TestResult("get_memory", "GET /api/memory/{id}")

            test_id = stored_memory_ids[0]

            if native_mem:
                try:
                    result.native_time_ms, result.native_result = time_operation(
                        native_mem.get_memory, test_id
                    )
                    print(f"  Native: {result.native_time_ms:.2f}ms")
                except Exception as e:
                    result.native_success = False
                    result.native_error = str(e)
                    print(f"  Native: FAILED - {e}")

            if rest_client:
                try:
                    result.rest_time_ms, result.rest_result = time_operation(
                        rest_client.get_memory, test_id
                    )
                    print(f"  REST: {result.rest_time_ms:.2f}ms")
                except Exception as e:
                    result.rest_success = False
                    result.rest_error = str(e)
                    print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 8. Context Summary
        # =====================================================================
        print("\n--- Context Summary ---")
        result = TestResult("context_summary", "POST /api/context_summary")

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.context_summary, max_items=5
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.context_summary, max_items=5
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 9. Brain State
        # =====================================================================
        print("\n--- Brain State ---")
        result = TestResult("brain_state", "GET /api/brain/{user_id}")

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.brain_state, longterm_limit=50
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.brain_state
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 10. Get Stats
        # =====================================================================
        print("\n--- Get Stats ---")
        result = TestResult("get_stats", "GET /api/users/{id}/stats")

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.get_stats
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.get_stats
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 11. Graph Stats (REST only)
        # =====================================================================
        if rest_client:
            print("\n--- Graph Stats (REST only) ---")
            result = TestResult("graph_stats", "GET /api/graph/{id}/stats")
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.graph_stats
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 12. Tracked Retrieve (REST only)
        # =====================================================================
        if rest_client:
            print("\n--- Tracked Retrieve (REST only) ---")
            result = TestResult("retrieve_tracked", "POST /api/retrieve/tracked")
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.retrieve_tracked, "authentication", limit=5
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 13. Reinforce (REST only)
        # =====================================================================
        if rest_client and stored_memory_ids:
            print("\n--- Reinforce (REST only) ---")
            result = TestResult("reinforce", "POST /api/reinforce")
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.reinforce, [stored_memory_ids[0]], outcome="helpful"
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 14. Advanced Search (REST only)
        # =====================================================================
        if rest_client:
            print("\n--- Advanced Search (REST only) ---")
            result = TestResult("advanced_search", "POST /api/search/advanced")
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.advanced_search, "performance", filters={"memory_type": "Discovery"}
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 15. Consolidate (REST only)
        # =====================================================================
        if rest_client:
            print("\n--- Consolidate (REST only) ---")
            result = TestResult("consolidate", "POST /api/consolidate")
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.consolidate
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 16. Forget by Tags
        # =====================================================================
        print("\n--- Forget by Tags ---")
        result = TestResult("forget_by_tags", "POST /api/forget/tags")

        # First add memory to delete
        if native_mem:
            native_mem.remember("Temp memory to delete", memory_type="Context", tags=["delete-me"])
        if rest_client:
            rest_client.remember("Temp memory to delete", memory_type="Context", tags=["delete-me"])

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.forget_by_tags, ["delete-me"]
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.forget_by_tags, ["delete-me"]
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 17. Forget by Importance
        # =====================================================================
        print("\n--- Forget by Importance ---")
        result = TestResult("forget_by_importance", "POST /api/forget/importance")

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.forget_by_importance, 0.99  # High threshold = nothing deleted
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.forget_by_importance, 0.99
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 18. Forget by Age
        # =====================================================================
        print("\n--- Forget by Age ---")
        result = TestResult("forget_by_age", "POST /api/forget/age")

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.forget_by_age, 999  # High age = nothing deleted
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.forget_by_age, 999
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 19. Forget by Pattern
        # =====================================================================
        if rest_client:
            print("\n--- Forget by Pattern (REST only) ---")
            result = TestResult("forget_by_pattern", "POST /api/forget/pattern")
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.forget_by_pattern, "^NEVER_MATCH_THIS_PATTERN$"
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 20. Forget by Date
        # =====================================================================
        print("\n--- Forget by Date ---")
        result = TestResult("forget_by_date", "POST /api/forget/date")

        # Use dates far in the past so nothing gets deleted
        old_start = "2000-01-01T00:00:00Z"
        old_end = "2000-01-02T00:00:00Z"

        if native_mem:
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.forget_by_date, old_start, old_end
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")

        if rest_client:
            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.forget_by_date, old_start, old_end
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
        results.append(result)

        # =====================================================================
        # 21. Batch Remember (REST only)
        # =====================================================================
        if rest_client:
            print("\n--- Batch Remember (REST only) ---")
            result = TestResult("batch_remember", "POST /api/batch_remember")

            batch_memories = [
                {"content": f"Batch memory {i}", "experience_type": "Observation", "tags": ["batch"]}
                for i in range(3)
            ]

            try:
                result.rest_time_ms, result.rest_result = time_operation(
                    rest_client.batch_remember, batch_memories
                )
                print(f"  REST: {result.rest_time_ms:.2f}ms ({result.rest_time_ms/3:.2f}ms/item)")
            except Exception as e:
                result.rest_success = False
                result.rest_error = str(e)
                print(f"  REST: FAILED - {e}")
            results.append(result)

        # =====================================================================
        # 22. Flush (Native only)
        # =====================================================================
        if native_mem:
            print("\n--- Flush (Native only) ---")
            result = TestResult("flush", "native.flush()")
            try:
                result.native_time_ms, result.native_result = time_operation(
                    native_mem.flush
                )
                print(f"  Native: {result.native_time_ms:.2f}ms")
            except Exception as e:
                result.native_success = False
                result.native_error = str(e)
                print(f"  Native: FAILED - {e}")
            results.append(result)

    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    return results


def print_summary(results: List[TestResult]):
    """Print summary table of all test results"""
    print("\n")
    print("=" * 100)
    print("TEST RESULTS SUMMARY")
    print("=" * 100)
    print(f"{'Test Name':<25} {'Endpoint':<35} {'Native (ms)':<15} {'REST (ms)':<15} {'Status'}")
    print("-" * 100)

    total_native = 0.0
    total_rest = 0.0
    native_tests = 0
    rest_tests = 0
    failed_tests = []

    for r in results:
        native_str = f"{r.native_time_ms:.2f}" if r.native_time_ms else "N/A"
        rest_str = f"{r.rest_time_ms:.2f}" if r.rest_time_ms else "N/A"

        status_parts = []
        if not r.native_success:
            status_parts.append(f"Native FAIL")
            failed_tests.append((r.name, "Native", r.native_error))
        if not r.rest_success:
            status_parts.append(f"REST FAIL")
            failed_tests.append((r.name, "REST", r.rest_error))
        if not status_parts:
            status_parts.append("OK")

        status = " | ".join(status_parts)
        print(f"{r.name:<25} {r.endpoint:<35} {native_str:<15} {rest_str:<15} {status}")

        if r.native_time_ms and r.native_success:
            total_native += r.native_time_ms
            native_tests += 1
        if r.rest_time_ms and r.rest_success:
            total_rest += r.rest_time_ms
            rest_tests += 1

    print("-" * 100)

    # Totals
    if native_tests > 0:
        print(f"{'NATIVE TOTAL':<25} {'':<35} {total_native:.2f} ms")
        print(f"{'NATIVE AVG':<25} {'':<35} {total_native/native_tests:.2f} ms/operation")
    if rest_tests > 0:
        print(f"{'REST TOTAL':<25} {'':<35} {'':<15} {total_rest:.2f} ms")
        print(f"{'REST AVG':<25} {'':<35} {'':<15} {total_rest/rest_tests:.2f} ms/operation")

    print("=" * 100)

    # Failed tests details
    if failed_tests:
        print("\nFAILED TESTS DETAILS:")
        print("-" * 80)
        for name, api_type, error in failed_tests:
            print(f"  {name} ({api_type}): {error[:60]}...")
        print("-" * 80)

    # Summary
    total_tests = len(results)
    passed = sum(1 for r in results if r.native_success and r.rest_success)
    print(f"\nTotal: {total_tests} tests | Passed: {passed} | Failed: {total_tests - passed}")


def main():
    results = run_tests()
    print_summary(results)

    # Return exit code
    all_success = all(r.native_success and r.rest_success for r in results)
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
