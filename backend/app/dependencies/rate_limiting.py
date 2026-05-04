"""
FastAPI dependencies for rate limiting.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth import get_current_user_optional
from app.utils.rate_limiter import (
    get_photo_request_limiter,
    get_api_general_limiter,
    get_auth_limiter,
)

logger = logging.getLogger(__name__)


async def check_photo_request_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Check rate limit for photo request creation.
    
    Limits: 10 requests per minute per customer/user.
    
    Returns:
        dict with rate limit info
    """
    limiter = get_photo_request_limiter()
    
    # Use customer_id if available, otherwise user email
    customer_id = request.headers.get("X-Customer-ID", None)
    client_host: str = request.client.host if request.client else "unknown"
    limit_key = f"customer_{customer_id}" if customer_id else f"user_{current_user.id if current_user else client_host}"
    
    allowed, info = limiter.is_allowed(limit_key)
    
    if not allowed:
        logger.warning(f"Rate limit exceeded for {limit_key}: {info['remaining']}/{info['limit']}")
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Limite: {info['limit']} por minuto. Reintentar en {info['reset_in_seconds']} segundos."
        )
    
    return info  # type: ignore[return-value]


async def check_api_rate_limit(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Check general API rate limit.
    
    Limits: 100 requests per minute per user.
    """
    limiter = get_api_general_limiter()
    client_host: str = request.client.host if request.client else "unknown"
    limit_key = f"user_{current_user.id}" if current_user else f"ip_{client_host}"
    
    allowed, info = limiter.is_allowed(limit_key)
    
    if not allowed:
        logger.warning(f"API rate limit exceeded for {limit_key}")
        raise HTTPException(
            status_code=429,
            detail=f"API rate limit exceeded: {info['limit']} requests per minute. Try again in {info['reset_in_seconds']}s."
        )
    
    return info  # type: ignore[return-value]


async def check_auth_rate_limit(request: Request) -> Dict[str, Any]:
    """
    Check authentication rate limit.
    
    Limits: 5 attempts per 5 minutes per IP.
    """
    limiter = get_auth_limiter()
    client_host: str = request.client.host if request.client else "unknown"
    limit_key = f"ip_{client_host}"
    
    allowed, info = limiter.is_allowed(limit_key)
    
    if not allowed:
        logger.warning(f"Auth rate limit exceeded for {limit_key}")
        raise HTTPException(
            status_code=429,
            detail=f"Too many authentication attempts. Try again in {info['reset_in_seconds']} seconds."
        )
    
    return info  # type: ignore[return-value]
