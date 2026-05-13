"""Async HTTP client for CCMS bill JSON only."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import CCMS_BILL_URL

_LOGGER = logging.getLogger(__name__)


def normalize_reference(ref: str) -> str:
    """Collapse whitespace; uppercase for display and consistency."""
    return "".join(ref.split()).upper()


def ccms_reference_14(ref: str) -> str:
    """CCMS bill endpoint requires exactly 14 digits."""
    digits = "".join(c for c in ref if c.isdigit())
    if len(digits) < 14:
        raise ValueError("reference must contain at least 14 digits for CCMS")
    return digits[:14]


class LescoApi:
    """CCMS web bill (public GET; no Power Smart)."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_get_ccms_bill(self, reference: str) -> dict[str, Any]:
        ref14 = ccms_reference_14(reference)
        url = f"{CCMS_BILL_URL}?reference={ref14}"
        async with self._session.get(
            url,
            headers={"Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise aiohttp.ClientResponseError(
                    request_info=resp.request_info,
                    history=resp.history,
                    status=resp.status,
                    message=text[:300] or resp.reason,
                )
            return await resp.json(content_type=None)
