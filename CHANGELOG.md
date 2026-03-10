# Changelog

All notable changes to this project will be documented in this file.

## 0.4.1 - 2026-03-10

- Fixed GitHub publish workflow permissions so PyPI checkout can read repository contents
- Fixed ClawHub publish workflow to use the Node.js payload workaround for `acceptLicenseTerms`

## 0.4.0 - 2026-03-10

- Switched the project license to Apache-2.0
- Removed built-in Telegram app credentials; users now provide `TG_API_ID` and `TG_API_HASH`
- Added YAML output support and documented YAML as the preferred agent format
- Added `tg recent`
- Added regex search with `tg search --regex`
- Added `tg refresh` as the recommended daily refresh entrypoint
- Added `--sync-first` to query commands
- Added `tg listen --persist` for automatic reconnect
- Improved local query safety with chat ambiguity detection and clearer `today` hints
- Added cron and systemd examples for scheduled refresh
