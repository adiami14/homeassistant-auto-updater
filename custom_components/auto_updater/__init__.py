"""Auto Updater – automatic Home Assistant update scheduler."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_change

from .const import (
    ALL_DAYS,
    CONF_AUTO_RESTART,
    CONF_BACKUP_BEFORE_UPDATE,
    CONF_MOBILE_NOTIFY_SERVICE,
    CONF_NOTIFY_MOBILE,
    CONF_UPDATE_DAYS,
    CONF_UPDATE_TIME,
    CONF_UPDATE_TYPES,
    DEFAULT_UPDATE_TIME,
    DEFAULT_UPDATE_TYPES,
    DOMAIN,
    SERVICE_UPDATE_NOW,
    SYSTEM_UPDATE_PATTERNS,
    UPDATE_TYPE_ADDONS,
    UPDATE_TYPE_CORE,
    UPDATE_TYPE_HACS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auto Updater from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = AutoUpdaterCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await coordinator.async_setup()
    await hass.config_entries.async_forward_entry_setups(entry, ["update"])
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: AutoUpdaterCoordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator:
        coordinator.async_unload()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["update"])
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class AutoUpdaterCoordinator:
    """Manage the scheduled update process."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsub_time: callable | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> dict:
        """Merge entry data + options (options override data)."""
        return {**self.entry.data, **self.entry.options}

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Register the scheduler and the manual-trigger service."""
        time_str: str = self.config.get(CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME)
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])

        active_days: list[str] = self.config.get(CONF_UPDATE_DAYS, ALL_DAYS)
        day_names = _day_labels(active_days)
        _LOGGER.info(
            "Auto Updater: scheduled at %02d:%02d on %s", hour, minute, day_names
        )

        self._unsub_time = async_track_time_change(
            self.hass,
            self._async_scheduled_run,
            hour=hour,
            minute=minute,
            second=0,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_NOW,
            self._async_service_update_now,
            schema=None,
        )

    def async_unload(self) -> None:
        """Cancel the scheduled task and remove the service."""
        if self._unsub_time:
            self._unsub_time()
            self._unsub_time = None
        if self.hass.services.has_service(DOMAIN, SERVICE_UPDATE_NOW):
            self.hass.services.async_remove(DOMAIN, SERVICE_UPDATE_NOW)

    # ------------------------------------------------------------------
    # Service / scheduler entry points
    # ------------------------------------------------------------------

    async def _async_scheduled_run(self, now: datetime) -> None:
        """Fired every day at the configured time — check day filter first."""
        active_days: list[str] = self.config.get(CONF_UPDATE_DAYS, ALL_DAYS)
        today = str(now.weekday())  # "0"=Mon … "6"=Sun
        if today not in active_days:
            _LOGGER.debug(
                "Auto Updater: skipping today (%s), not in active days %s",
                today,
                active_days,
            )
            return
        await self._async_run_updates(now)

    async def _async_service_update_now(self, _call: ServiceCall) -> None:
        """Handle the auto_updater.update_now service call (bypasses day filter)."""
        await self._async_run_updates(datetime.now())

    # ------------------------------------------------------------------
    # Core update logic
    # ------------------------------------------------------------------

    async def _async_run_updates(self, _now: datetime) -> None:
        """Check for updates and install them."""
        _LOGGER.info("Auto Updater: starting update run")
        cfg = self.config
        update_types: list[str] = cfg.get(CONF_UPDATE_TYPES, DEFAULT_UPDATE_TYPES)
        notify_mobile: bool = cfg.get(CONF_NOTIFY_MOBILE, True)
        notify_service: str = cfg.get(CONF_MOBILE_NOTIFY_SERVICE, "notify")
        backup_first: bool = cfg.get(CONF_BACKUP_BEFORE_UPDATE, True)
        auto_restart: bool = cfg.get(CONF_AUTO_RESTART, False)

        pending = self._get_pending_updates(update_types)
        if not pending:
            _LOGGER.info("Auto Updater: no updates available")
            return

        names = [s.attributes.get("friendly_name", s.entity_id) for s in pending]
        _LOGGER.info("Auto Updater: %d update(s) found — %s", len(pending), names)

        # Separate core from the rest: core update restarts HA, so do it last
        core_updates = [
            s for s in pending
            if SYSTEM_UPDATE_PATTERNS[UPDATE_TYPE_CORE] in s.entity_id
        ]
        other_updates = [
            s for s in pending
            if SYSTEM_UPDATE_PATTERNS[UPDATE_TYPE_CORE] not in s.entity_id
        ]

        if backup_first:
            await self._create_backup()

        updated: list[str] = []
        skipped: list[str] = []
        failed: list[str] = []

        for state in other_updates:
            status, desc = await self._install_update(state)
            if status == "ok":
                updated.append(desc)
            elif status == "skipped":
                skipped.append(desc)
            else:
                failed.append(desc)
            await asyncio.sleep(3)

        # Determine whether we will restart after notifying
        will_restart = auto_restart and (updated or core_updates) and not core_updates
        # (if core_updates exist, HA restarts automatically — no extra restart needed)

        await self._send_notifications(
            updated, skipped, failed, core_updates, will_restart,
            notify_mobile, notify_service,
        )

        # Trigger core update last (causes automatic HA restart)
        for state in core_updates:
            installed = state.attributes.get("installed_version", "?")
            latest = state.attributes.get("latest_version", "?")
            _LOGGER.info(
                "Auto Updater: triggering Core update %s → %s (HA will restart)",
                installed, latest,
            )
            try:
                await self.hass.services.async_call(
                    "update", "install",
                    {"entity_id": state.entity_id},
                    blocking=False,
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Auto Updater: Core update failed to start: %s", err)

        # Auto-restart if requested and no core update (which already restarts)
        if will_restart:
            _LOGGER.info("Auto Updater: restarting Home Assistant as requested…")
            await asyncio.sleep(5)  # give notifications time to flush
            try:
                await self.hass.services.async_call(
                    "homeassistant", "restart", {}, blocking=False
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Auto Updater: restart failed: %s", err)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _create_backup(self) -> None:
        """Request a HA backup before updating."""
        _LOGGER.info("Auto Updater: creating backup…")
        try:
            await self.hass.services.async_call(
                "hassio", "backup_full", {}, blocking=False
            )
            await asyncio.sleep(5)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Auto Updater: backup failed (skipping): %s", err)

    async def _install_update(self, state) -> tuple[str, str]:
        """Install a single update entity. Returns (status, description).

        Status: 'ok' | 'skipped' | 'failed'
        """
        entity_id: str = state.entity_id
        name: str = state.attributes.get("friendly_name", entity_id)
        installed: str = state.attributes.get("installed_version", "?")
        latest: str = state.attributes.get("latest_version", "?")
        desc = f"{name}: {installed} → {latest}"

        # UpdateEntityFeature.INSTALL = 1 — skip read-only informational entities
        supported = state.attributes.get("supported_features", 0)
        if not (supported & 1):
            _LOGGER.info("Auto Updater: skipped %s — does not support install", name)
            return "skipped", f"{name} (manual install required)"

        try:
            await asyncio.wait_for(
                self.hass.services.async_call(
                    "update", "install",
                    {"entity_id": entity_id},
                    blocking=True,
                ),
                timeout=300,
            )
            _LOGGER.info("Auto Updater: ✓ %s", desc)
            return "ok", desc
        except asyncio.TimeoutError:
            _LOGGER.warning("Auto Updater: timed out updating %s", name)
            return "failed", f"{name}: timed out"
        except Exception as err:  # noqa: BLE001
            err_str = str(err)
            if "requires Home Assistant" in err_str:
                _LOGGER.info("Auto Updater: skipped %s — %s", name, err_str)
                return "skipped", f"{name} ({err_str})"
            _LOGGER.error("Auto Updater: failed to update %s: %s", name, err_str)
            return "failed", f"{name}: {err_str}"

    # ------------------------------------------------------------------
    # Entity filtering
    # ------------------------------------------------------------------

    def _get_pending_updates(self, update_types: list[str]) -> list:
        """Return update entities that have an update available, filtered by type."""
        ent_reg = er.async_get(self.hass)
        result: list = []
        seen: set[str] = set()

        for state in self.hass.states.async_all("update"):
            if state.entity_id in seen:
                continue
            # Include state "on" (update available) OR skipped/dismissed
            # (state "off" but installed_version != latest_version).
            installed = state.attributes.get("installed_version")
            latest = state.attributes.get("latest_version")
            has_update = state.state == STATE_ON or (
                installed and latest and installed != latest
            )
            if not has_update:
                continue

            entity_id = state.entity_id
            reg_entry = ent_reg.async_get(entity_id)
            platform: str = reg_entry.platform if reg_entry else ""
            matched = False

            # HA system components (core, os, supervisor)
            for utype, pattern in SYSTEM_UPDATE_PATTERNS.items():
                if pattern in entity_id and utype in update_types:
                    result.append(state)
                    seen.add(entity_id)
                    matched = True
                    break

            if matched:
                continue

            # HACS updates
            if UPDATE_TYPE_HACS in update_types and platform == "hacs":
                result.append(state)
                seen.add(entity_id)
                continue

            # Add-ons: anything not matching system patterns and not HACS
            if UPDATE_TYPE_ADDONS in update_types:
                is_system = any(p in entity_id for p in SYSTEM_UPDATE_PATTERNS.values())
                if not is_system and platform != "hacs":
                    result.append(state)
                    seen.add(entity_id)

        return result

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    async def _send_notifications(
        self,
        updated: list[str],
        skipped: list[str],
        failed: list[str],
        pending_core: list,
        will_restart: bool,
        notify_mobile: bool,
        notify_service: str,
    ) -> None:
        """Send persistent + optional mobile notification."""
        lines: list[str] = []

        if updated:
            lines.append("✅ **Updated successfully:**")
            lines.extend(f"• {item}" for item in updated)

        if skipped:
            if lines:
                lines.append("")
            lines.append("⏭️ **Skipped (requires newer HA Core):**")
            lines.extend(f"• {item}" for item in skipped)

        if failed:
            if lines:
                lines.append("")
            lines.append("❌ **Failed:**")
            lines.extend(f"• {item}" for item in failed)

        if pending_core:
            if lines:
                lines.append("")
            lines.append("🔄 **Core update starting (HA will restart):**")
            for s in pending_core:
                name = s.attributes.get("friendly_name", s.entity_id)
                inst = s.attributes.get("installed_version", "?")
                lat = s.attributes.get("latest_version", "?")
                lines.append(f"• {name}: {inst} → {lat}")

        if will_restart:
            if lines:
                lines.append("")
            lines.append("🔁 **HA restarting to apply updates…**")

        if not lines:
            return

        total = len(updated) + len(pending_core)
        title = f"Auto Updater: {total} updated"
        if skipped:
            title += f", {len(skipped)} skipped"
        if failed:
            title += f", {len(failed)} failed"
        if will_restart or pending_core:
            title += " — restarting"

        message_md = "\n".join(lines)

        await self.hass.services.async_call(
            "persistent_notification", "create",
            {
                "title": title,
                "message": message_md,
                "notification_id": f"{DOMAIN}_update_result",
            },
        )

        if notify_mobile and notify_service:
            plain = "\n".join(
                line.replace("**", "")
                for line in lines
                if line
            )
            svc_parts = notify_service.strip().split(".", 1)
            svc_domain = svc_parts[0] if len(svc_parts) == 2 else "notify"
            svc_name = svc_parts[1] if len(svc_parts) == 2 else notify_service.strip()
            try:
                await self.hass.services.async_call(
                    svc_domain, svc_name,
                    {"title": title, "message": plain},
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(
                    "Auto Updater: mobile notification via %s.%s failed: %s",
                    svc_domain, svc_name, err,
                )


def _day_labels(day_keys: list[str]) -> str:
    """Convert list of weekday keys to a readable string."""
    from .const import DAYS_OF_WEEK
    if set(day_keys) == set(ALL_DAYS):
        return "every day"
    return ", ".join(DAYS_OF_WEEK.get(k, k) for k in sorted(day_keys))
