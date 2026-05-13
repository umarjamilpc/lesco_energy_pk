# LESCO CCMS bill (HACS)

Home Assistant custom integration that reads the **public CCMS web bill JSON** for a LESCO consumer using the **reference number** only (no Power Smart login).

## Install (HACS)

1. Add [umarjamilpc/lesco_energy_pk](https://github.com/umarjamilpc/lesco_energy_pk) as a **Custom repository** (category: Integration).
2. Install, restart Home Assistant.
3. **Settings → Devices & services → Add integration → LESCO CCMS Bill**.
4. Enter your **reference number** (CCMS uses the first **14 digits**).

## Entities (short names)

- **CCMS status** — `ok` / `error`; attributes hold bill fields (consumer, dates, tariff, etc.).
- **Net PKR**, **Due PKR**, **Net kWh** (billed net units for the period), **Imp/Exp pk/off kWh** for the bill month.
- **Hist month**, **Hist rows**, **Hist kWh**, **Hist pay PKR** — billing history summary.
- Twelve **meter** sensors: `Imp off prev/now/Δ`, `Imp pk …`, `Exp off …`, `Exp pk …` (cumulative reads and billed delta per register).

Update interval defaults to **6 hours** (`const.py`).

## Upgrading from v1.x (Power Smart)

Older entries stored phone, password, and reference. On upgrade, the integration **migrates** to **reference-only**; remove unused secrets from your secrets file if you had any. Restart Home Assistant after updating.

## Disclaimer

Unofficial integration; use at your own risk.
