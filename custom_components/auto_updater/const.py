"""Constants for Auto Updater."""

DOMAIN = "auto_updater"

CONF_UPDATE_TIME = "update_time"
CONF_UPDATE_TYPES = "update_types"
CONF_NOTIFY_MOBILE = "notify_mobile"
CONF_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
CONF_BACKUP_BEFORE_UPDATE = "backup_before_update"
CONF_TEST_MODE = "test_mode"
CONF_AUTO_RESTART = "auto_restart"
CONF_UPDATE_DAYS = "update_days"

UPDATE_TYPE_CORE = "core"
UPDATE_TYPE_OS = "os"
UPDATE_TYPE_SUPERVISOR = "supervisor"
UPDATE_TYPE_ADDONS = "addons"
UPDATE_TYPE_HACS = "hacs"

UPDATE_TYPES: dict[str, str] = {
    UPDATE_TYPE_CORE: "Home Assistant Core",
    UPDATE_TYPE_OS: "Home Assistant OS",
    UPDATE_TYPE_SUPERVISOR: "Home Assistant Supervisor",
    UPDATE_TYPE_ADDONS: "Add-ons",
    UPDATE_TYPE_HACS: "HACS",
}

# Days of week: value = Python weekday() integer (0=Mon … 6=Sun)
DAYS_OF_WEEK: dict[str, str] = {
    "0": "Monday",
    "1": "Tuesday",
    "2": "Wednesday",
    "3": "Thursday",
    "4": "Friday",
    "5": "Saturday",
    "6": "Sunday",
}

ALL_DAYS = list(DAYS_OF_WEEK.keys())  # default = run every day

DEFAULT_UPDATE_TIME = "03:30:00"
DEFAULT_UPDATE_TYPES = [
    UPDATE_TYPE_CORE,
    UPDATE_TYPE_OS,
    UPDATE_TYPE_SUPERVISOR,
    UPDATE_TYPE_ADDONS,
]

# Substrings in entity_id that identify HA system update entities
SYSTEM_UPDATE_PATTERNS: dict[str, str] = {
    UPDATE_TYPE_CORE: "home_assistant_core_update",
    UPDATE_TYPE_OS: "home_assistant_operating_system_update",
    UPDATE_TYPE_SUPERVISOR: "home_assistant_supervisor_update",
}

SERVICE_UPDATE_NOW = "update_now"
