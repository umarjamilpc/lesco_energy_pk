"""Data update coordinator."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LescoApi, normalize_reference
from .const import CONF_PASSWORD, CONF_PHONE, CONF_REFERENCE, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def flatten_bill(bill_root: dict[str, Any]) -> dict[str, Any]:
    """Map CCMS bill.basicInfo into flat string attributes for HA."""
    out: dict[str, Any] = {}
    bill = bill_root.get("bill")
    if not isinstance(bill, dict):
        return out
    bi = bill.get("basicInfo")
    if not isinstance(bi, dict):
        return out
    mapping = [
        ("ref_no", "refNo"),
        ("consumer_name", "consumerName"),
        ("bill_month", "billMonth"),
        ("net_bill", "netBill"),
        ("curr_amount_due", "currAmntDue"),
        ("tot_cur_cons", "totCurCons"),
        ("imp_peak_units", "imp_p_units"),
        ("imp_offpeak_units", "imp_op_units"),
        ("exp_peak_units", "exp_p_units"),
        ("exp_offpeak_units", "exp_op_units"),
        ("bill_due_date", "billDueDate"),
        ("meter_read_date", "meterReadDate"),
        ("consumer_contact", "consumerContactNo"),
    ]
    for key, src in mapping:
        v = bi.get(src)
        if v is not None:
            out[key] = str(v)
    return out


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

        try:
            ccms = await self.api.async_get_ccms_bill(reference)
        except Exception as err:
            raise UpdateFailed(f"CCMS bill failed: {err}") from err

        bill_flat = flatten_bill(ccms if isinstance(ccms, dict) else {})
        monthly_raw = ""
        try:
            import json as _json

            monthly_raw = _json.dumps(monthly, ensure_ascii=False)[:8000]
        except (TypeError, ValueError):
            monthly_raw = str(monthly)[:8000]

        monthly_msg = ""
        if isinstance(monthly, dict) and monthly.get("message") is not None:
            monthly_msg = str(monthly["message"])

        return {
            "reference": normalize_reference(reference),
            "token_last_ok": True,
            "monthly_raw": monthly_raw,
            "monthly_message": monthly_msg,
            "ccms_message": str(ccms.get("message", ""))
            if isinstance(ccms, dict)
            else "",
            **bill_flat,
        }
