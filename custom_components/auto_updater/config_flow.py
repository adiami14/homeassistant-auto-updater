"""Config flow for Auto Updater."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    ALL_DAYS,
    CONF_AUTO_RESTART,
    CONF_BACKUP_BEFORE_UPDATE,
    CONF_MOBILE_NOTIFY_SERVICE,
    CONF_NOTIFY_MOBILE,
    CONF_UPDATE_DAYS,
    CONF_UPDATE_TIME,
    CONF_UPDATE_TYPES,
    DAYS_OF_WEEK,
    DEFAULT_UPDATE_TIME,
    DEFAULT_UPDATE_TYPES,
    DOMAIN,
    UPDATE_TYPES,
)


def _build_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            # ── Schedule ──────────────────────────────────────────────
            vol.Required(
                CONF_UPDATE_TIME,
                default=d.get(CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME),
            ): selector.TimeSelector(),
            vol.Required(
                CONF_UPDATE_DAYS,
                default=d.get(CONF_UPDATE_DAYS, ALL_DAYS),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=k, label=v)
                        for k, v in DAYS_OF_WEEK.items()
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            # ── What to update ────────────────────────────────────────
            vol.Required(
                CONF_UPDATE_TYPES,
                default=d.get(CONF_UPDATE_TYPES, DEFAULT_UPDATE_TYPES),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=k, label=v)
                        for k, v in UPDATE_TYPES.items()
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            # ── Post-update actions ───────────────────────────────────
            vol.Optional(
                CONF_BACKUP_BEFORE_UPDATE,
                default=d.get(CONF_BACKUP_BEFORE_UPDATE, True),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_AUTO_RESTART,
                default=d.get(CONF_AUTO_RESTART, False),
            ): selector.BooleanSelector(),
            # ── Notifications ─────────────────────────────────────────
            vol.Optional(
                CONF_NOTIFY_MOBILE,
                default=d.get(CONF_NOTIFY_MOBILE, True),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_MOBILE_NOTIFY_SERVICE,
                default=d.get(CONF_MOBILE_NOTIFY_SERVICE, "notify"),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
        }
    )


class AutoUpdaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Auto Updater", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AutoUpdaterOptionsFlow:
        return AutoUpdaterOptionsFlow()


class AutoUpdaterOptionsFlow(config_entries.OptionsFlow):
    """Handle options updates."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(current),
        )
