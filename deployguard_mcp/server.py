from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from deployguard_mcp.tools.analyze_pr import analyze_pr
from deployguard_mcp.tools.history import get_historical_risk
from deployguard_mcp.tools.risk import (
    get_risk_explanation,
    get_risk_score,
)

mcp = FastMCP(
    "DeployGuard",
    log_level="WARNING",
)


@mcp.tool()
async def analyze_pull_request(repository_id: str, pr_id: int) -> dict:
    return await analyze_pr(
        repository_id=repository_id,
        pr_id=pr_id,
    )


@mcp.tool()
def risk_score(analysis_id: int) -> dict:
    return get_risk_score(analysis_id=analysis_id)


@mcp.tool()
def explain_risk(analysis_id: int) -> dict:
    return get_risk_explanation(analysis_id=analysis_id)


@mcp.tool()
def historical_risk(repository_id: str, paths: list[str]) -> dict:
    return get_historical_risk(
        repository_id=repository_id,
        paths=paths,
    )


if __name__ == "__main__":
    mcp.run()
