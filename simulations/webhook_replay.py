import argparse
import asyncio
import random

import httpx


def build_payload(pr_id: int, repo_id: str, event_type: str = "git.pullrequest.created"):
    return {
        "subscriptionId": "demo-subscription",
        "notificationId": pr_id,
        "id": f"evt-{pr_id}",
        "eventType": event_type,
        "resource": {
            "pullRequestId": pr_id,
            "repository": {"id": repo_id},
        },
    }


async def send_webhook(base_url: str, pr_id: int, repo_id: str, event_type: str):
    payload = build_payload(pr_id=pr_id, repo_id=repo_id, event_type=event_type)
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(f"{base_url}/api/v1/webhook/azure-devops", json=payload)
        return res.status_code, res.text


async def main(base_url: str, count: int, start_pr_id: int, repo_id: str):
    tasks = []
    for i in range(count):
        pr_id = start_pr_id + i
        event_type = random.choice(["git.pullrequest.created", "git.pullrequest.updated"])
        tasks.append(send_webhook(base_url, pr_id, repo_id, event_type))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    ok = sum(1 for r in results if isinstance(r, tuple) and r[0] == 200)
    failed = len(results) - ok

    print("\n=== Webhook Replay Report ===")
    print(f"Total: {len(results)}")
    print(f"Accepted: {ok}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay Azure DevOps webhook events for DeployGuard")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--start-pr-id", type=int, default=1000)
    parser.add_argument("--repo-id", default="demo-repo")
    args = parser.parse_args()

    asyncio.run(main(args.base_url, args.count, args.start_pr_id, args.repo_id))
