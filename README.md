# LESCO Power Smart & CCMS (HACS)

Custom integration for Home Assistant that signs in to **Power Smart** (phone + password), uses the returned **JWT automatically** (no manual token), fetches **monthly consumption** history, and reads the latest **CCMS bill** details (reference uses the first **14 digits** for CCMS; full ref is kept for Power Smart).

## Install (HACS)

1. In HACS, add this repository as a **Custom repository** (category: Integration).
2. Install the integration, then restart Home Assistant.
3. **Settings → Devices & services → Add integration → LESCO Power Smart & CCMS**.
4. Enter **reference number**, **phone number**, and **password**. The config flow validates by signing in; the stored entry does **not** include a token (tokens are refreshed on each poll).

## Manual install

Copy the folder `custom_components/lesco` into your Home Assistant `config` directory and restart.

## Entities

- **Overview**: `ok` / `error` plus attributes (bill fields, raw monthly JSON snippet, messages).
- **Net bill**, **Current amount due**, **Billed month total consumption** when CCMS returns those fields.

Update interval defaults to **6 hours** (see `const.py`).

## Disclaimer

This is an unofficial integration. Use at your own risk; credentials are stored in the Home Assistant config entry.
