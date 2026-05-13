"""Data update coordinator — CCMS bill only."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LescoApi, normalize_reference
from .bill_data import (
    billing_history_json,
    flatten_basic_info,
    format_due_date_display,
    parse_billing_history,
    parse_meters_info,
)
from .const import CONF_REFERENCE, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _safe_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


class LescoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll CCMS bill JSON on an interval."""

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
        reference = self.config_entry.data[CONF_REFERENCE]

        try:
            ccms = await self.api.async_get_ccms_bill(reference)
        except Exception as err:
            raise UpdateFailed(f"CCMS bill failed: {err}") from err

        ccms_dict = ccms if isinstance(ccms, dict) else {}
        bill_flat = flatten_basic_info(ccms_dict)
        if "bill_due_date" in bill_flat:
            formatted = format_due_date_display(bill_flat["bill_due_date"])
            if formatted:
                bill_flat["bill_due_date"] = formatted
        meters = parse_meters_info(ccms_dict)
        hist_rows = parse_billing_history(ccms_dict)

        hist_latest_month = ""
        hist_latest_units: float | None = None
        hist_latest_payment: float | None = None
        if hist_rows:
            last = hist_rows[-1]
            hist_latest_month = last.get("month", "")
            hist_latest_units = _safe_float(last.get("units"))
            hist_latest_payment = _safe_float(last.get("payment_pkr"))

        return {
            "reference": normalize_reference(reference),
            "ccms_message": str(ccms_dict.get("message", "")),
            "billing_history_json": billing_history_json(hist_rows),
            "billing_history_entries": hist_rows,
            "hist_latest_month": hist_latest_month,
            "hist_latest_units_kwh": hist_latest_units,
            "hist_latest_payment_pkr": hist_latest_payment,
            "billing_history_count": len(hist_rows),
            **bill_flat,
            **meters,
        }
