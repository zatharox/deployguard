import argparse
import asyncio
import random
import statistics
import time
from collections import Counter

import httpx


SCENARIOS = ["low", "medium", "high", "critical"]


async def worker(base_url: str, requests_per_user: int, reset_first: bool, semaphore: asyncio.Semaphore, stats: dict):
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(requests_per_user):
            scenario = random.choice(SCENARIOS)
            reset = reset_first and i == 0
            url = f"{base_url}/api/v1/analysis/demo/run/{scenario}?reset={'true' if reset else 'false'}"

            async with semaphore:
                start = time.perf_counter()
                try:
                    response = await client.post(url)
                    latency_ms = (time.perf_counter() - start) * 1000
                    stats["latencies"].append(latency_ms)

                    if response.status_code == 200:
                        payload = response.json()
                        analysis = payload.get("analysis", {})
                        stats["success"] += 1
                        stats["risk_levels"][analysis.get("risk_level", "unknown")] += 1
                    else:
                        stats["errors"] += 1
                except Exception:
                    stats["errors"] += 1


async def run_simulation(base_url: str, users: int, requests_per_user: int, max_in_flight: int, reset_first: bool):
    stats = {
        "success": 0,
        "errors": 0,
        "latencies": [],
        "risk_levels": Counter(),
    }

    semaphore = asyncio.Semaphore(max_in_flight)
    tasks = [
        worker(base_url, requests_per_user, reset_first, semaphore, stats)
        for _ in range(users)
    ]

    start = time.perf_counter()
    await asyncio.gather(*tasks)
    duration = time.perf_counter() - start

    total_requests = users * requests_per_user
    latencies = sorted(stats["latencies"])
    p50 = latencies[int(0.50 * len(latencies))] if latencies else 0
    p95 = latencies[int(0.95 * len(latencies)) - 1] if len(latencies) >= 1 else 0
    p99 = latencies[int(0.99 * len(latencies)) - 1] if len(latencies) >= 1 else 0

    print("\n=== DeployGuard Production Simulation Report ===")
    print(f"Base URL: {base_url}")
    print(f"Virtual users: {users}")
    print(f"Requests per user: {requests_per_user}")
    print(f"Total requests: {total_requests}")
    print(f"Duration: {duration:.2f}s")
    print(f"Throughput: {total_requests / duration:.2f} req/s" if duration > 0 else "Throughput: N/A")
    print(f"Success: {stats['success']}")
    print(f"Errors: {stats['errors']}")
    print(f"Error rate: {(stats['errors'] / total_requests) * 100:.2f}%")

    if latencies:
        print("\nLatency (ms):")
        print(f"  avg: {statistics.mean(latencies):.2f}")
        print(f"  p50: {p50:.2f}")
        print(f"  p95: {p95:.2f}")
        print(f"  p99: {p99:.2f}")
        print(f"  max: {max(latencies):.2f}")

    print("\nRisk distribution:")
    for level in ["low", "medium", "high", "unknown"]:
        print(f"  {level}: {stats['risk_levels'][level]}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run production-like load simulation for DeployGuard")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="DeployGuard base URL")
    parser.add_argument("--users", type=int, default=20, help="Concurrent virtual users")
    parser.add_argument("--requests-per-user", type=int, default=25, help="Requests per user")
    parser.add_argument("--max-in-flight", type=int, default=50, help="Max in-flight requests")
    parser.add_argument("--reset-first", action="store_true", help="Reset DB only on first request per user")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run_simulation(
            base_url=args.base_url,
            users=args.users,
            requests_per_user=args.requests_per_user,
            max_in_flight=args.max_in_flight,
            reset_first=args.reset_first,
        )
    )
