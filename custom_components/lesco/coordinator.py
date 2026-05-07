"""Data update coordinator."""

from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LescoApi, normalize_reference
from .bill_data import (
    billing_history_json,
    flatten_basic_info,
    parse_billing_history,
    parse_meters_info,
    summarize_powersmart_daily,
)
from .const import CONF_PASSWORD, CONF_PHONE, CONF_REFERENCE, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _trunc_json(obj: Any, limit: int = 8000) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        s = str(obj)
    if len(s) > limit:
        return s[: limit - 20] + "…(truncated)"
    return s


def _safe_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


class LescoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll Power Smart + CCMS; obtain a fresh JWT on every update via sign-in."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: LescoApi,
    ) -> None:
        self.config_entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        phone = self.config_entry.data[CONF_PHONE]
        password = self.config_entry.data[CONF_PASSWORD]
        reference = self.config_entry.data[CONF_REFERENCE]

        try:
            token = await self.api.async_sign_in(phone, password)
        except KeyError as err:
            raise UpdateFailed(f"Power Smart login: no token in response ({err})") from err
        except Exception as err:
            raise UpdateFailed(f"Power Smart login failed: {err}") from err

        try:
            monthly = await self.api.async_get_monthly_consumption(token, reference)
        except Exception as err:
            raise UpdateFailed(f"monthlyConsumption failed: {err}") from err

        daily_raw = await self.api.async_get_daily_consumption(token, reference)
        daily_summary = summarize_powersmart_daily(daily_raw)

        try:
            ccms = await self.api.async_get_ccms_bill(reference)
        except Exception as err:
            raise UpdateFailed(f"CCMS bill failed: {err}") from err

        ccms_dict = ccms if isinstance(ccms, dict) else {}
        bill_flat = flatten_basic_info(ccms_dict)
        meters = parse_meters_info(ccms_dict)
        hist_rows = parse_billing_history(ccms_dict)

        monthly_msg = ""
        if isinstance(monthly, dict) and monthly.get("message") is not None:
            monthly_msg = str(monthly["message"])

        hist_latest_month = ""
        hist_latest_units: float | None = None
        hist_latest_payment: float | None = None
        if hist_rows:
            last = hist_rows[-1]
            hist_latest_month = last.get("month", "")
            hist_latest_units = _safe_float(last.get("units"))
            hist_latest_payment = _safe_float(last.get("payment_pkr"))

        data: dict[str, Any] = {
            "reference": normalize_reference(reference),
            "token_last_ok": True,
            "monthly_raw": _trunc_json(monthly),
            "monthly_message": monthly_msg,
            "powersmart_daily_raw": _trunc_json(daily_raw) if daily_raw is not None else "",
            "ccms_message": str(ccms_dict.get("message", "")),
            "billing_history_json": billing_history_json(hist_rows),
            "billing_history_entries": hist_rows,
            "hist_latest_month": hist_latest_month,
            "hist_latest_units_kwh": hist_latest_units,
            "hist_latest_payment_pkr": hist_latest_payment,
            "billing_history_count": len(hist_rows),
            **bill_flat,
            **meters,
            **daily_summary,
        }

        if daily_raw is not None and not daily_summary.get("daily_last_row_json"):
            _LOGGER.debug(
                "dailyConsumption returned data but no recognized fields; "
                "check powersmart_daily_raw attribute on overview."
            )

        return data
