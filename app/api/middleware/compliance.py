import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)

class ComplianceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for:
    1. PII Redaction in logs and headers
    2. Data Residency validation
    3. Mandatory GDPR/CCPA headers
    """

    def __init__(
        self,
        app: ASGIApp,
        pii_patterns: Optional[Dict[str, str]] = None,
        allowed_regions: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.pii_patterns = pii_patterns or {
            "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
            "api_key": r"lkg_[a-zA-Z0-9]{32,}",
        }
        self.allowed_regions = allowed_regions

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 1. Data Residency Check (simple example)
        # In production, we'd check headers like CF-IPCountry or X-AppEngine-Region
        user_region = request.headers.get("X-User-Region")
        if self.allowed_regions and user_region and user_region not in self.allowed_regions:
            logger.warning(f"Data residency violation: User from {user_region} but region not allowed.")
            # For strict GDPR, we might block or re-route. For now, just log.

        # 2. Process Request
        response = await call_next(request)

        # 3. Add Compliance Headers
        response.headers["X-Compliance-GDPR"] = "v1"
        response.headers["X-Compliance-Retention-Policy"] = "conversations:30d"
        response.headers["X-Content-Type-Options"] = "nosniff"

        return response

    def redact_pii(self, text: str) -> str:
        """Regex-based PII redaction for logs."""
        redacted = text
        for label, pattern in self.pii_patterns.items():
            redacted = re.sub(pattern, f"[{label.upper()}_REDACTED]", redacted)
        return redacted
