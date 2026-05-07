"""Sensors: CCMS bill, meter readings, import/export, billing history, Power Smart daily."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REFERENCE, DOMAIN
from .coordinator import LescoCoordinator

# Large / redundant keys omitted from Overview attributes (use dedicated sensors).
# Keep overview readable; full table lives on the billing_history sensor.
_OVERVIEW_SKIP_ATTRS = frozenset({"billing_history_json", "billing_history_entries"})

# Meter register keys (CCMS cumulative reads + billed delta per register).
_METER_KEYS: list[tuple[str, str, str | None, int]] = [
    ("meter_import_offpeak_previous_kwh", "Import off-peak previous reading", "kWh", 3),
    ("meter_import_offpeak_present_kwh", "Import off-peak present reading", "kWh", 3),
    ("meter_import_offpeak_billed_kwh", "Import off-peak billed units", "kWh", 3),
    ("meter_import_peak_previous_kwh", "Import peak previous reading", "kWh", 3),
    ("meter_import_peak_present_kwh", "Import peak present reading", "kWh", 3),
    ("meter_import_peak_billed_kwh", "Import peak billed units", "kWh", 3),
    ("meter_export_offpeak_previous_kwh", "Export off-peak previous reading", "kWh", 3),
    ("meter_export_offpeak_present_kwh", "Export off-peak present reading", "kWh", 3),
    ("meter_export_offpeak_billed_kwh", "Export off-peak billed units", "kWh", 3),
    ("meter_export_peak_previous_kwh", "Export peak previous reading", "kWh", 3),
    ("meter_export_peak_present_kwh", "Export peak present reading", "kWh", 3),
    ("meter_export_peak_billed_kwh", "Export peak billed units", "kWh", 3),
]

_DAILY_KEYS: list[tuple[str, str]] = [
    ("daily_imp_peak", "Power Smart daily import peak (last row)"),
    ("daily_imp_offpeak", "Power Smart daily import off-peak (last row)"),
    ("daily_exp_peak", "Power Smart daily export peak (last row)"),
    ("daily_exp_offpeak", "Power Smart daily export off-peak (last row)"),
]


def _build_sensor_descriptions() -> tuple[SensorEntityDescription, ...]:
    out: list[SensorEntityDescription] = [
        SensorEntityDescription(key="overview", name="Overview"),
        SensorEntityDescription(
            key="billing_history",
            name="Billing history (latest month)",
        ),
        SensorEntityDescription(
            key="billing_history_count",
            name="Billing history rows",
        ),
        SensorEntityDescription(
            key="daily_last_date",
            name="Power Smart daily last date",
        ),
    ]
    for key, name, unit, prec in [
        ("net_bill", "Net bill", "PKR", 0),
        ("curr_amount_due", "Current amount due", "PKR", 0),
        (
            "tot_cur_cons",
            "Billed net units (CCMS)",
            "kWh",
            3,
        ),
        ("imp_peak_units", "Import peak units (bill month)", "kWh", 3),
        ("imp_offpeak_units", "Import off-peak units (bill month)", "kWh", 3),
        ("exp_peak_units", "Export peak units (bill month)", "kWh", 3),
        ("exp_offpeak_units", "Export off-peak units (bill month)", "kWh", 3),
        ("hist_latest_units_kwh", "Latest history month units", "kWh", 3),
        ("hist_latest_payment_pkr", "Latest history month payment", "PKR", 0),
    ]:
        kwargs: dict = {
            "key": key,
            "name": name,
            "native_unit_of_measurement": unit,
            "suggested_display_precision": prec,
        }
        out.append(SensorEntityDescription(**kwargs))
    for key, name, unit, prec in _METER_KEYS:
        out.append(
            SensorEntityDescription(
                key=key,
                name=name,
                native_unit_of_measurement=unit,
                suggested_display_precision=prec,
            )
        )
    for key, name in _DAILY_KEYS:
        out.append(
            SensorEntityDescription(
                key=key,
                name=name,
                native_unit_of_measurement="kWh",
                suggested_display_precision=3,
            )
        )
    return tuple(out)


SENSORS: tuple[SensorEntityDescription, ...] = _build_sensor_descriptions()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Add sensors."""
    coordinator: LescoCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[LescoSensor] = [LescoSensor(coordinator, desc) for desc in SENSORS]
    async_add_entities(entities)


def _to_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    cleaned = str(raw).replace(",", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


class LescoSensor(CoordinatorEntity[LescoCoordinator], SensorEntity):
    """Sensor fed by coordinator data."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LescoCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )
        ref = coordinator.config_entry.data.get(CONF_REFERENCE, "")
        dev_name = f"LESCO {str(ref)[:18]}" if ref else "LESCO"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=dev_name,
            manufacturer="PITC",
            model="Power Smart + CCMS",
        )

    @property
    def native_value(self) -> str | float | int | None:
        """State value."""
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data
        key = self.entity_description.key

        if key == "overview":
            return "ok" if self.coordinator.last_update_success else "error"

        if key == "billing_history":
            m = data.get("hist_latest_month")
            return str(m) if m else None

        if key == "billing_history_count":
            n = data.get("billing_history_count")
            if n is None:
                return None
            try:
                return int(n)
            except (TypeError, ValueError):
                return None

        if key == "daily_last_date":
            v = data.get("daily_last_date")
            return str(v) if v else None

        raw = data.get(key)
        if raw is None or raw == "":
            return None
        return _to_float(raw)

    @property
    def extra_state_attributes(self) -> dict:
        """Overview: bill + API context. Billing history: full table."""
        if not self.coordinator.data:
            return {}
        data = self.coordinator.data
        key = self.entity_description.key

        if key == "overview":
            return {
                k: v
                for k, v in data.items()
                if v is not None and k not in _OVERVIEW_SKIP_ATTRS
            }

        if key == "billing_history":
            return {
                "latest_units_kwh": data.get("hist_latest_units_kwh"),
                "latest_payment_pkr": data.get("hist_latest_payment_pkr"),
                "entries": data.get("billing_history_entries", []),
                "history_json": data.get("billing_history_json", ""),
            }

        if key == "daily_last_date":
            return {"last_row_json": data.get("daily_last_row_json")}

        return {}
