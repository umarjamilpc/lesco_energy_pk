# LESCO CCMS bill (HACS)

Home Assistant custom integration that reads the **public CCMS web bill JSON** for a LESCO consumer using the **reference number** only (no Power Smart login).

## Install (HACS)

1. Add [umarjamilpc/lesco_energy_pk](https://github.com/umarjamilpc/lesco_energy_pk) as a **Custom repository** (category: Integration).
2. Install, restart Home Assistant.
3. **Settings → Devices & services → Add integration → LESCO CCMS Bill**.
4. Enter your **reference number** (CCMS uses the first **14 digits**).

### HACS version display (commit hash vs `v3.x.x`)

HACS uses the **Git tag name from a published GitHub Release** as the version (e.g. `v3.1.4`). If you only track the default branch, it shows the **first 7 characters of the last commit** (e.g. `61dfacb`).

- In HACS, open the integration → **Redownload** / install and pick a **Release** (e.g. `v3.1.4`), not `main`, so updates show semantic versions.
- This repository creates a **GitHub Release** automatically whenever a `v*.*.*` tag is pushed (GitHub Actions). **Tags alone are not enough** — see [HACS publishing: Versions](https://hacs.dev/docs/publish/start).

## Entities (UPPERCASE names, `ha_sensor.docx`)

- **CCMS STATUS** — `OK` / `ERROR`; attributes hold bill fields (consumer, tariff, etc.).
- **DUE DATE**, **READING DATE**, **ISSUE DATE** — text from CCMS when present.
- **LAST BILLING MONTH** — latest history month; attributes hold full **entries** table.
- **REMAINING UNITS** (kWh), **LAST BILLING MONTH COST** (PKR).
- **CURRENT IMP(O)/IMP(P)/EXP(O)/EXP(P) UNITS** (kWh) for the bill month.
- Eight **meter** sensors: **PREVIOUS/PRESENT** cumulative reads per register (IMP/EXP, O/P).

Update interval defaults to **6 hours** (`const.py`).

## Upgrading from v1.x (Power Smart)

Older entries stored phone, password, and reference. On upgrade, the integration **migrates** to **reference-only**; remove unused secrets from your secrets file if you had any. Restart Home Assistant after updating.

## Disclaimer

Unofficial integration; use at your own risk.
