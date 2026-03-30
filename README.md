# Auto Updater for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs-shield]][hacs]
[![Project Maintenance][maintenance-shield]][maintenance]

Automatically schedule and install Home Assistant updates — Core, OS, Supervisor, Add-ons, and HACS integrations — at a time you choose, with notifications and optional auto-restart.

---

## Features

- **Scheduled updates** — Run at a configurable time and on selected days of the week
- **Selective update types** — Choose which types to update: Core, OS, Supervisor, Add-ons, HACS
- **Backup before update** — Optionally create a full backup before applying any changes
- **Auto-restart** — Optionally restart Home Assistant after non-Core updates complete
- **Persistent notifications** — A summary notification shows what was updated, skipped, or failed
- **Mobile notifications** — Optionally push to any `notify` service (e.g. companion app)
- **Manual trigger** — Call `auto_updater.update_now` any time to run immediately, bypassing the day filter
- **Skipped-update detection** — Catches updates dismissed in the UI (`installed != latest`) so nothing is silently missed

---

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations**
3. Click the **⋮** menu → **Custom repositories**
4. Add `https://github.com/adiami14/homeassistant-auto-updater` as category **Integration**
5. Find **Auto Updater** and click **Download**
6. Restart Home Assistant
7. Go to **Settings → Devices & Services → Add Integration** and search for **Auto Updater**

### Manual

1. Download the latest release from the [Releases page][releases]
2. Copy `custom_components/auto_updater/` into your HA config `custom_components/` folder
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**

---

## Configuration

All settings are configurable via the UI — no YAML needed.

| Option | Default | Description |
|--------|---------|-------------|
| Update time | `03:30` | Time of day to run updates |
| Run on days | All 7 days | Select which days of the week to run |
| Update types | Core, OS, Supervisor, Add-ons | Which update categories to install |
| Backup before update | `On` | Create a full backup before updating |
| Auto-restart | `Off` | Restart HA after non-Core updates |
| Mobile notification | `On` | Send a push notification when done |
| Notification service | `notify` | Service to use (e.g. `notify.mobile_app_my_phone`) |

To reconfigure, go to **Settings → Devices & Services → Auto Updater → Configure**.

---

## Services

### `auto_updater.update_now`

Triggers an immediate update run, bypassing the day-of-week filter. Useful for testing or for running an update on demand.

```yaml
service: auto_updater.update_now
```

---

## Notifications

After each run you will receive a persistent HA notification summarising:

- ✅ **Updated successfully** — `Name: old_version → new_version`
- ⏭️ **Skipped** — Updates that require a newer HA Core version
- ❌ **Failed** — Updates that encountered an error
- 🔄 **Core update** — Core updates are fired last (they restart HA automatically)
- 🔁 **HA restarting** — If auto-restart is enabled

---

## Automation example

Run an update check on demand from a button press:

```yaml
automation:
  trigger:
    - platform: state
      entity_id: input_button.run_updates
  action:
    - service: auto_updater.update_now
```

---

## Contributing

Pull requests and issues are welcome! Please:

- Use the **Bug Report** template for bugs
- Use the **Feature Request** template for new ideas
- Check existing issues before opening a new one

---

## License

MIT — see [LICENSE](LICENSE)

---

[releases-shield]: https://img.shields.io/github/release/adiami14/homeassistant-auto-updater.svg?style=for-the-badge
[releases]: https://github.com/adiami14/homeassistant-auto-updater/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/adiami14/homeassistant-auto-updater.svg?style=for-the-badge
[commits]: https://github.com/adiami14/homeassistant-auto-updater/commits/main
[license-shield]: https://img.shields.io/github/license/adiami14/homeassistant-auto-updater.svg?style=for-the-badge
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40adiami14-blue.svg?style=for-the-badge
[maintenance]: https://github.com/adiami14
