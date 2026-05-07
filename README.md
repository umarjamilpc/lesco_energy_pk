# LESCO Power Smart & CCMS (HACS)

Custom integration for Home Assistant that signs in to **Power Smart** (phone + password), uses the returned **JWT automatically** (no manual token), calls **Power Smart** history APIs where available, and reads the latest **CCMS** web bill JSON (reference uses the first **14 digits** for CCMS; full ref is kept for Power Smart).

## Install (HACS)

1. In HACS, add this repository as a **Custom repository** (category: Integration).
2. Install the integration, then restart Home Assistant.
3. **Settings → Devices & services → Add integration → LESCO Power Smart & CCMS**.
4. Enter **reference number**, **phone number**, and **password**. The config flow validates by signing in; the stored entry does **not** include a token (tokens are refreshed on each poll).

## Manual install

Copy the folder `custom_components/lesco` into your Home Assistant `config` directory and restart.

## Net metering: why “billed net units” can be negative

On **AMI net metering** bills, CCMS field `totCurCons` is the **net billed energy for the month** (import vs export interaction), **not** “total kWh you imported”. A value like **−421** matches the bill’s net column (e.g. export-heavy months). For **import and export kWh** for the billed month, use the **Import peak / off-peak** and **Export peak / off-peak** sensors, and the **meter register** sensors (previous / present cumulative reads and billed delta per register), which mirror the web bill / PDF register table.

## Entities (summary)

| Area | What you get |
|------|----------------|
| **CCMS bill** | Net bill, current amount due, billed net units, import/export **units for the bill month**, tariff, meter read date, due date, etc. (many also on **Overview** attributes). |
| **Meter readings** | Twelve sensors: for each of import off-peak / import peak / export off-peak / export peak — **previous kWh reading**, **present kWh reading**, **billed kWh** (from CCMS `metersInfo`, same layout as the web bill). |
| **Billing history** | **Billing history (latest month)** state = latest month label; attributes include **`entries`**: up to 13 rows with `month`, `units`, `payment_pkr`, `assessment_pkr` (CCMS `histInfo`). Separate sensors for **latest history month units** and **latest history month payment**. **Billing history rows** = row count. |
| **Power Smart** | **Monthly** response remains in **Overview** (`monthly_raw`). **Daily** uses `POST …/getHistory/dailyConsumption` (same body as monthly); if the server accepts it, **Power Smart daily import/export (last row)** sensors and **Power Smart daily last date** fill in; otherwise check `last_row_json` on the daily date sensor and open an issue with a redacted sample so field names can be mapped. |

Update interval defaults to **6 hours** (see `const.py`).

## Disclaimer

This is an unofficial integration. Use at your own risk; credentials are stored in the Home Assistant config entry.
