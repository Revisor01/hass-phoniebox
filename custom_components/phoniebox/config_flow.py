# mypy: disable-error-code="no-any-return"
"""Adds config flow for Blueprint."""

from typing import Any, override
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_COVER_URL, CONF_MQTT_BASE_TOPIC, CONF_PHONIEBOX_NAME, DOMAIN

DOCS_URL = "https://github.com/c0un7-z3r0/hass-phoniebox"


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    _errors: dict[str, str]

    def __init__(self) -> None:
        """Initialize."""
        self._errors = {}

    @staticmethod
    @callback
    @override
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return PhonieboxOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            if user_input[CONF_PHONIEBOX_NAME] and user_input[CONF_MQTT_BASE_TOPIC]:
                return self.async_create_entry(
                    title=user_input[CONF_PHONIEBOX_NAME], data=user_input
                )
            self._errors["base"] = "auth"

            return self._show_config_form(user_input)

        # Provide defaults for form
        user_input = {CONF_PHONIEBOX_NAME: "", CONF_MQTT_BASE_TOPIC: "phoniebox"}

        return self._show_config_form(user_input)

    def _show_config_form(
        self, user_input: dict[str, str]
    ) -> config_entries.ConfigFlowResult:
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PHONIEBOX_NAME, default=user_input[CONF_PHONIEBOX_NAME]
                    ): str,
                    vol.Required(
                        CONF_MQTT_BASE_TOPIC, default=user_input[CONF_MQTT_BASE_TOPIC]
                    ): str,
                }
            ),
            errors=self._errors,
            description_placeholders={"docs_url": DOCS_URL},
        )


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


class PhonieboxOptionsFlow(config_entries.OptionsFlow):
    """Options for an existing Phoniebox."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask for the address of the cover image."""
        errors: dict[str, str] = {}
        current = self.config_entry.options.get(CONF_COVER_URL, "")

        if user_input is not None:
            cover_url = user_input.get(CONF_COVER_URL, "").strip()
            options = {
                key: value
                for key, value in self.config_entry.options.items()
                if key != CONF_COVER_URL
            }
            if not cover_url:
                return self.async_create_entry(data=options)
            if _is_http_url(cover_url):
                return self.async_create_entry(
                    data={**options, CONF_COVER_URL: cover_url}
                )
            errors[CONF_COVER_URL] = "invalid_url"
            current = cover_url

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_COVER_URL, description={"suggested_value": current}
                    ): str,
                }
            ),
            errors=errors,
        )
