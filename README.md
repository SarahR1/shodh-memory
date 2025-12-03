<p align="center">
  <img src="assets/logo.png" width="120" alt="Shodh-Memory">
</p>

<h1 align="center">Shodh-Memory</h1>

<p align="center">
  Local memory system for AI agents on edge devices
</p>

<p align="center">
  <a href="https://github.com/varun29ankuS/shodh-memory/actions"><img src="https://github.com/varun29ankuS/shodh-memory/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
</p>

---

## Overview

Shodh-Memory stores and retrieves text memories using semantic search. Runs offline without cloud services.

**Use cases:** Robots, drones, IoT devices, privacy-focused applications.

## Demo

```bash
# Start server
$ ./shodh-memory-server
2024-12-03T10:00:00 INFO  Starting Shodh-Memory server on 0.0.0.0:3030
2024-12-03T10:00:01 INFO  Models downloaded: ~/.cache/shodh-memory/models/minilm-l6
2024-12-03T10:00:02 INFO  Server ready

# Store a memory
$ curl -s -X POST http://localhost:3030/api/record \
  -H "Content-Type: application/json" \
  -d '{"user_id": "robot-001", "content": "Obstacle detected at X=5, Y=10", "experience_type": "observation"}' | jq
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "created"
}

# Search memories
$ curl -s -X POST http://localhost:3030/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"user_id": "robot-001", "query": "obstacle", "max_results": 5}' | jq
{
  "memories": [
    {
      "memory_id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "Obstacle detected at X=5, Y=10",
      "relevance": 0.92,
      "created_at": "2024-12-03T10:00:05Z"
    }
  ]
}
```

## Installation

**From source (requires Rust 1.70+):**

```bash
git clone https://github.com/varun29ankuS/shodh-memory
cd shodh-memory
cargo build --release
./target/release/shodh-memory-server
```

Models (~34MB) download automatically on first use.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/record` | Store memory |
| `POST` | `/api/retrieve` | Search memories |
| `GET` | `/api/memory/:id` | Get memory |
| `DELETE` | `/api/memory/:id` | Delete memory |
| `GET` | `/health` | Health check |

## Python Client

```python
import requests

BASE = "http://localhost:3030"

# Store
requests.post(f"{BASE}/api/record", json={
    "user_id": "robot-001",
    "content": "Battery at 20%",
    "experience_type": "sensor"
})

# Search
response = requests.post(f"{BASE}/api/retrieve", json={
    "user_id": "robot-001",
    "query": "battery",
    "max_results": 5
})
print(response.json())
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 3030 | Server port |
| `STORAGE_PATH` | ./shodh_memory_data | Data directory |
| `RUST_LOG` | info | Log level |

## Requirements

- Rust 1.70+ (build)
- ~50MB disk (models)
- ~100MB RAM

## Status

Early-stage. Works for basic use cases. Not yet tested extensively on edge hardware.

## License

Apache 2.0

## Links

- [Website](https://shodh-rag.com/memory)
- [Issues](https://github.com/varun29ankuS/shodh-memory/issues)
- Email: 29.varuns@gmail.com
