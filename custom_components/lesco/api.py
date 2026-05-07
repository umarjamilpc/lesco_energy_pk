"""Async API client for Power Smart + CCMS."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import CCMS_BILL_URL, POWERSMART_BASE

_LOGGER = logging.getLogger(__name__)


def normalize_reference(ref: str) -> str:
    """Collapse whitespace; uppercase for Power Smart refNo."""
    return "".join(ref.split()).upper()


def ccms_reference_14(ref: str) -> str:
    """CCMS bill endpoint requires exactly 14 digits."""
    digits = "".join(c for c in ref if c.isdigit())
    if len(digits) < 14:
        raise ValueError("reference must contain at least 14 digits for CCMS")
    return digits[:14]


def extract_token(body: dict[str, Any]) -> str:
    """Parse JWT from various Power Smart signIn response shapes."""
    if isinstance(body.get("token"), str):
        return body["token"]
    for k in ("accessToken", "jwt", "authToken"):
        if isinstance(body.get(k), str):
            return body[k]
    data = body.get("data")
    if isinstance(data, dict):
        for k in ("token", "accessToken", "jwt"):
            if isinstance(data.get(k), str):
                return data[k]
    if isinstance(data, list) and data and isinstance(data[0], dict):
        t = data[0].get("token")
        if isinstance(t, str):
            return t
    raise KeyError("token")


class LescoApi:
    """Power Smart login + monthlyConsumption; CCMS bill (no Power Smart token)."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_sign_in(self, phone: str, password: str) -> str:
        url = f"{POWERSMART_BASE}/appUser/signIn"
        payload = {"contactNo": phone.strip(), "password": password}
        async with self._session.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            try:
                body: dict[str, Any] = await resp.json(content_type=None)
            except aiohttp.ContentTypeError:
                body = {}
            if resp.status != 200:
                text = str(body)[:500] if body else await resp.text()
                _LOGGER.warning("signIn HTTP %s: %s", resp.status, text)
                raise aiohttp.ClientResponseError(
                    request_info=resp.request_info,
                    history=resp.history,
                    status=resp.status,
                    message=text[:200] if isinstance(text, str) else resp.reason,
                )
        return extract_token(body)

    async def async_get_monthly_consumption(
        self, token: str, reference: str
    ) -> dict[str, Any] | list[Any]:
        url = f"{POWERSMART_BASE}/getHistory/monthlyConsumption"
        ref = normalize_reference(reference)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        async with self._session.post(
            url,
            json={"refNo": ref},
            headers=headers,
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
