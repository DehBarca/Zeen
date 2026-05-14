# Simple Run

Quick reference for spinning up the stack and running the API tests.

## 1. Reset state (recommended before every run)

```bash
docker-compose down -v
```

`-v` wipes the volumes so MongoDB / Cassandra / Dgraph / ChromaDB start clean. Skipping this step is the most common cause of test failures (duplicate users, leftover content, stale indexes).

## 2. Start the stack

```bash
docker-compose up --build
```

Wait until all services report healthy. Service URLs:

| Service     | URL                            |
| ----------- | ------------------------------ |
| Frontend    | http://localhost:5173          |
| API         | http://localhost:8000          |
| Swagger UI  | http://localhost:8000/docs     |
| Health      | http://localhost:8000/health   |

## 3. Run the API tests

In a second terminal:

```bash
./test_all_endpoints.sh             # compact: only ✓ / ✗ status lines
./test_all_endpoints.sh --detailed  # verbose: also prints request + response bodies
```

The script hits every endpoint under `localhost:8000/api/v1` and prints a pass/fail summary at the end. Use `--detailed` when a test fails and you need to see the actual payloads.

## Stop

```bash
docker-compose down       # stop, keep data
docker-compose down -v    # stop, wipe data (use before next test run)
```
