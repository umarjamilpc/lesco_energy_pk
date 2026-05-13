"""Sensors: CCMS bill, meters, import/export, billing history."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REFERENCE, DOMAIN
from .coordinator import LescoCoordinator

_OVERVIEW_SKIP_ATTRS = frozenset({"billing_history_json", "billing_history_entries"})

_METER_KEYS: list[tuple[str, str, str | None, int]] = [
    ("meter_import_offpeak_previous_kwh", "Imp off prev", "kWh", 3),
    ("meter_import_offpeak_present_kwh", "Imp off now", "kWh", 3),
    ("meter_import_offpeak_billed_kwh", "Imp off Δ", "kWh", 3),
    ("meter_import_peak_previous_kwh", "Imp pk prev", "kWh", 3),
    ("meter_import_peak_present_kwh", "Imp pk now", "kWh", 3),
    ("meter_import_peak_billed_kwh", "Imp pk Δ", "kWh", 3),
    ("meter_export_offpeak_previous_kwh", "Exp off prev", "kWh", 3),
    ("meter_export_offpeak_present_kwh", "Exp off now", "kWh", 3),
    ("meter_export_offpeak_billed_kwh", "Exp off Δ", "kWh", 3),
    ("meter_export_peak_previous_kwh", "Exp pk prev", "kWh", 3),
    ("meter_export_peak_present_kwh", "Exp pk now", "kWh", 3),
    ("meter_export_peak_billed_kwh", "Exp pk Δ", "kWh", 3),
]


def _build_sensor_descriptions() -> tuple[SensorEntityDescription, ...]:
    out: list[SensorEntityDescription] = [
        SensorEntityDescription(key="overview", name="CCMS status"),
        SensorEntityDescription(key="billing_history", name="Hist month"),
        SensorEntityDescription(key="billing_history_count", name="Hist rows"),
    ]
    for key, name, unit, prec in [
        ("net_bill", "Net PKR", "PKR", 0),
        ("curr_amount_due", "Due PKR", "PKR", 0),
        ("tot_cur_cons", "Net kWh", "kWh", 3),
        ("imp_peak_units", "Imp pk kWh", "kWh", 3),
        ("imp_offpeak_units", "Imp off kWh", "kWh", 3),
        ("exp_peak_units", "Exp pk kWh", "kWh", 3),
        ("exp_offpeak_units", "Exp off kWh", "kWh", 3),
        ("hist_latest_units_kwh", "Hist kWh", "kWh", 3),
        ("hist_latest_payment_pkr", "Hist pay PKR", "PKR", 0),
    ]:
        out.append(
            SensorEntityDescription(
                key=key,
                name=name,
                native_unit_of_measurement=unit,
                suggested_display_precision=prec,
            )
        )
    for key, name, unit, prec in _METER_KEYS:
        out.append(
            SensorEntityDescription(
                key=key,
                name=name,
                native_unit_of_measurement=unit,
                suggested_display_precision=prec,
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
            model="CCMS bill",
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

        raw = data.get(key)
        if raw is None or raw == "":
            return None
        return _to_float(raw)

    @property
    def extra_state_attributes(self) -> dict:
        """Overview: bill context. Billing history: full table."""
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

        return {}
