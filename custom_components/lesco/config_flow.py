"""Config flow: reference only — validate via CCMS bill GET."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LescoApi, ccms_reference_14
from .const import CONF_REFERENCE, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REFERENCE): str,
    }
)


def _ccms_bill_looks_valid(body: dict[str, Any]) -> bool:
    """True if JSON looks like a CCMS bill payload."""
    if not isinstance(body.get("bill"), dict):
        return False
    bi = body["bill"].get("basicInfo")
    return isinstance(bi, dict)


class LescoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle UI flow."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            ref = user_input[CONF_REFERENCE].strip()
            try:
                ccms_reference_14(ref)
            except ValueError:
                errors["base"] = "invalid_reference"
            else:
                session = async_get_clientsession(self.hass)
                api = LescoApi(session)
                try:
                    body = await api.async_get_ccms_bill(ref)
                except aiohttp.ClientResponseError as err:
                    if err.status in (400, 404, 422):
                        errors["base"] = "invalid_reference"
                    else:
                        _LOGGER.exception("CCMS HTTP error")
                        errors["base"] = "cannot_connect"
                except aiohttp.ClientError:
                    _LOGGER.exception("CCMS connection error")
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("CCMS fetch failed")
                    errors["base"] = "unknown"
                else:
                    if not _ccms_bill_looks_valid(body if isinstance(body, dict) else {}):
                        errors["base"] = "invalid_reference"
                    else:
                        data = {CONF_REFERENCE: ref}
                        uid = ccms_reference_14(ref)
                        await self.async_set_unique_id(uid)
                        self._abort_if_unique_id_configured()
                        title = f"LESCO {uid}"
                        return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
