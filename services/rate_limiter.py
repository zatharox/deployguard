"""
Rate limiting middleware
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict, Tuple
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Simple in-memory rate limiter (use Redis for distributed systems)"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier (IP + user if authenticated)"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        client_ip = forwarded_for.split(",")[0] if forwarded_for else request.client.host
        
        # Include user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        return f"{client_ip}:{user_id}" if user_id else client_ip
    
    def _clean_old_requests(self, client_id: str, current_time: float):
        """Remove requests outside the time window"""
        cutoff = current_time - self.window_size
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]
    
    def check_rate_limit(self, request: Request) -> Tuple[bool, int]:
        """
        Check if request is within rate limit
        Returns: (is_allowed, remaining_requests)
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        self._clean_old_requests(client_id, current_time)
        
        request_count = len(self.requests[client_id])
        
        if request_count >= self.requests_per_minute:
            logger.warning("rate_limit_exceeded",
                          client_id=client_id,
                          count=request_count)
            return False, 0
        
        self.requests[client_id].append(current_time)
        remaining = self.requests_per_minute - (request_count + 1)
        
        return True, remaining


# Global rate limiter instances
rate_limiters = {
    "default": RateLimiter(requests_per_minute=60),
    "analysis": RateLimiter(requests_per_minute=30),
    "webhook": RateLimiter(requests_per_minute=100)
}


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    
    # Skip rate limiting for health checks
    if request.url.path in ["/api/v1/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    # Choose rate limiter based on path
    if "/webhook" in request.url.path:
        limiter = rate_limiters["webhook"]
    elif "/analysis" in request.url.path:
        limiter = rate_limiters["analysis"]
    else:
        limiter = rate_limiters["default"]
    
    is_allowed, remaining = limiter.check_rate_limit(request)
    
    if not is_allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Try again in 60 seconds."
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Remaining": "0"
            }
        )
    
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response
