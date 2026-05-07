"""Config flow: phone, password, reference — validate via Power Smart sign-in."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LescoApi
from .const import CONF_PASSWORD, CONF_PHONE, CONF_REFERENCE, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PHONE): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REFERENCE): str,
    }
)


class LescoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle UI flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = LescoApi(session)
            try:
                token = await api.async_sign_in(
                    user_input[CONF_PHONE], user_input[CONF_PASSWORD]
                )
                if not token or not str(token).strip():
                    errors["base"] = "invalid_auth"
            except aiohttp.ClientResponseError as err:
                if err.status in (401, 403, 400):
                    errors["base"] = "invalid_auth"
                else:
                    _LOGGER.exception("Sign-in HTTP error")
                    errors["base"] = "cannot_connect"
            except KeyError:
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                _LOGGER.exception("Sign-in connection error")
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Sign-in failed")
                errors["base"] = "unknown"

            if not errors:
                data = {
                    CONF_PHONE: user_input[CONF_PHONE].strip(),
                    CONF_PASSWORD: user_input[CONF_PASSWORD].strip(),
                    CONF_REFERENCE: user_input[CONF_REFERENCE].strip(),
                }
                ref = data[CONF_REFERENCE]
                phone = data[CONF_PHONE]
                await self.async_set_unique_id(f"{phone}_{ref}".lower().replace(" ", ""))
                self._abort_if_unique_id_configured()
                title = f"LESCO {ref[:20]}"
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
