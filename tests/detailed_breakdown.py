#!/usr/bin/env python3
"""
Detailed timing breakdown for each operation - Native vs REST
"""
import time
import os
import sys
import json
import tempfile
import urllib.request
import urllib.error

os.environ["ORT_DYLIB_PATH"] = r"C:\Users\Varun Sharma\OneDrive\Documents\Roshera\Vector-DB\vectora\kalki-v2\libs\onnxruntime.dll"

BASE_URL = "http://127.0.0.1:3030"  # Use IPv4 directly to avoid Windows IPv6 fallback delay
API_KEY = "sk-shodh-dev-4f8b2c1d9e3a7f5b6d2c8e4a1b9f7d3c"
ITERATIONS = 3

def rest_request(endpoint, method="POST", data=None):
    """Make REST API request."""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def check_server():
    try:
        urllib.request.urlopen(f"{BASE_URL}/health", timeout=2)
        return True
    except:
        return False

print("=" * 90)
print("DETAILED TIMING BREAKDOWN: Native Python vs REST API")
print("=" * 90)

# Check server
server_available = check_server()
print(f"REST Server: {'AVAILABLE' if server_available else 'NOT RUNNING'}")
if not server_available:
    print("ERROR: Start the server first with: ./target/release/shodh-memory-server.exe")
    sys.exit(1)

# Import native
from shodh_memory import Memory

# Create temp storage for native
temp_dir = tempfile.mkdtemp(prefix="shodh_breakdown_")
memory = Memory(storage_path=temp_dir)

# Warmup
print("\n--- WARMUP (not timed) ---")
memory.remember("warmup content for model loading", memory_type="Context")
memory.recall("warmup query")
rest_request("/api/remember", data={"user_id": "breakdown-user", "content": "warmup REST", "memory_type": "Context"})
rest_request("/api/recall", data={"user_id": "breakdown-user", "query": "warmup", "limit": 5})
print("    Warmup complete.\n")

def measure_operation(name, native_fn, rest_fn, iterations=ITERATIONS):
    """Measure and display detailed breakdown."""
    print(f"\n{'='*90}")
    print(f"OPERATION: {name}")
    print(f"{'='*90}")

    native_times = []
    rest_times = []

    print(f"\n{'Iter':<6} {'Native (ms)':<15} {'REST (ms)':<15} {'Diff (ms)':<15} {'Winner':<10}")
    print("-" * 70)

    for i in range(iterations):
        # Native
        start = time.perf_counter()
        native_fn()
        native_t = (time.perf_counter() - start) * 1000
        native_times.append(native_t)

        # REST
        start = time.perf_counter()
        rest_fn()
        rest_t = (time.perf_counter() - start) * 1000
        rest_times.append(rest_t)

        diff = rest_t - native_t
        winner = "Native" if native_t < rest_t else "REST"
        print(f"{i+1:<6} {native_t:<15.2f} {rest_t:<15.2f} {diff:+<15.2f} {winner:<10}")

    native_avg = sum(native_times) / len(native_times)
    rest_avg = sum(rest_times) / len(rest_times)

    print("-" * 70)
    print(f"{'AVG':<6} {native_avg:<15.2f} {rest_avg:<15.2f} {rest_avg-native_avg:+<15.2f} {'Native' if native_avg < rest_avg else 'REST':<10}")
    print(f"{'MIN':<6} {min(native_times):<15.2f} {min(rest_times):<15.2f}")
    print(f"{'MAX':<6} {max(native_times):<15.2f} {max(rest_times):<15.2f}")

    return native_avg, rest_avg

results = []

# 1. REMEMBER
n, r = measure_operation(
    "REMEMBER (embedding + NER + storage)",
    lambda: memory.remember(f"Test memory about machine learning {time.time()}", memory_type="Learning"),
    lambda: rest_request("/api/remember", data={"user_id": "breakdown-user", "content": f"Test memory REST {time.time()}", "memory_type": "Learning"})
)
results.append(("remember", n, r))

# 2. RECALL
n, r = measure_operation(
    "RECALL (embedding + vector search)",
    lambda: memory.recall("machine learning neural networks", limit=5),
    lambda: rest_request("/api/recall", data={"user_id": "breakdown-user", "query": "machine learning", "limit": 5})
)
results.append(("recall", n, r))

# 3. LIST_MEMORIES
n, r = measure_operation(
    "LIST_MEMORIES (database read only)",
    lambda: memory.list_memories(limit=10),
    lambda: rest_request(f"/api/list/breakdown-user", method="GET")
)
results.append(("list_memories", n, r))

# 4. CONTEXT_SUMMARY
n, r = measure_operation(
    "CONTEXT_SUMMARY (aggregation)",
    lambda: memory.context_summary(),
    lambda: rest_request("/api/context_summary", data={"user_id": "breakdown-user"})
)
results.append(("context_summary", n, r))

# 5. GET_STATS
n, r = measure_operation(
    "GET_STATS (metadata only)",
    lambda: memory.get_stats(),
    lambda: rest_request(f"/api/users/breakdown-user/stats", method="GET")
)
results.append(("get_stats", n, r))

# 6. RECALL_BY_TAGS (no embedding)
memory.remember("Tagged memory for testing", memory_type="Context", tags=["test-tag"])
rest_request("/api/remember", data={"user_id": "breakdown-user", "content": "Tagged REST memory", "tags": ["test-tag"]})

n, r = measure_operation(
    "RECALL_BY_TAGS (no embedding needed)",
    lambda: memory.recall_by_tags(["test-tag"], limit=5),
    lambda: rest_request("/api/recall/tags", data={"user_id": "breakdown-user", "tags": ["test-tag"], "limit": 5})
)
results.append(("recall_by_tags", n, r))

# 7. RECALL_BY_DATE (no embedding)
from datetime import datetime, timedelta
start_date = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
end_date = datetime.utcnow().isoformat() + "Z"

n, r = measure_operation(
    "RECALL_BY_DATE (no embedding needed)",
    lambda: memory.recall_by_date(start_date, end_date, limit=5),
    lambda: rest_request("/api/recall/date", data={"user_id": "breakdown-user", "start": start_date, "end": end_date, "limit": 5})
)
results.append(("recall_by_date", n, r))

# 8. BRAIN_STATE
n, r = measure_operation(
    "BRAIN_STATE (3-tier visualization)",
    lambda: memory.brain_state(),
    lambda: rest_request(f"/api/brain/breakdown-user", method="GET")
)
results.append(("brain_state", n, r))

# 9. GRAPH_STATS
n, r = measure_operation(
    "GRAPH_STATS (Hebbian graph)",
    lambda: memory.graph_stats(),
    lambda: rest_request(f"/api/graph/breakdown-user/stats", method="GET")
)
results.append(("graph_stats", n, r))

# Summary
print("\n")
print("=" * 90)
print("SUMMARY TABLE")
print("=" * 90)
print(f"\n{'Operation':<25} {'Native (ms)':<15} {'REST (ms)':<15} {'HTTP Overhead':<15} {'Speedup':<10}")
print("-" * 80)

total_native = 0
total_rest = 0
for op, n, r in results:
    overhead = r - n
    speedup = r / n if n > 0 else 0
    print(f"{op:<25} {n:<15.2f} {r:<15.2f} {overhead:+<15.2f} {speedup:.1f}x")
    total_native += n
    total_rest += r

print("-" * 80)
print(f"{'TOTAL':<25} {total_native:<15.2f} {total_rest:<15.2f} {total_rest-total_native:+<15.2f} {total_rest/total_native:.1f}x")

print("""
ANALYSIS:
=========
- remember/recall ~50ms: ONNX embedding dominates (same in both)
- DB operations <1ms native, ~2ms REST: HTTP/JSON overhead visible
- The ~50ms proves embedding generation is included (not cached)
""")

# Cleanup
import shutil
shutil.rmtree(temp_dir, ignore_errors=True)
