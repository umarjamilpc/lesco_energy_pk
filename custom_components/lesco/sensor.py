"""Sensors: CCMS bill, meters, import/export, billing history (per ha_sensor.docx)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REFERENCE, DOMAIN
from .coordinator import LescoCoordinator

_OVERVIEW_SKIP_ATTRS = frozenset({"billing_history_json", "billing_history_entries"})

# String state (not kWh / PKR).
_STRING_VALUE_KEYS = frozenset({"bill_due_date", "meter_read_date", "issue_date"})

_METER_KEYS: list[tuple[str, str, str | None, int]] = [
    ("meter_import_offpeak_previous_kwh", "PREVIOUS IMP(O) UNITS", "kWh", 3),
    ("meter_import_offpeak_present_kwh", "PRESENT IMP(O) UNITS", "kWh", 3),
    ("meter_import_peak_previous_kwh", "PREVIOUS IMP(P) UNITS", "kWh", 3),
    ("meter_import_peak_present_kwh", "PRESENT IMP(P) UNITS", "kWh", 3),
    ("meter_export_offpeak_previous_kwh", "PREVIOUS EXP(O) UNITS", "kWh", 3),
    ("meter_export_offpeak_present_kwh", "PRESENT EXP(O) UNITS", "kWh", 3),
    ("meter_export_peak_previous_kwh", "PREVIOUS EXP(P) UNITS", "kWh", 3),
    ("meter_export_peak_present_kwh", "PRESENT EXP(P) UNITS", "kWh", 3),
]


def _build_sensor_descriptions() -> tuple[SensorEntityDescription, ...]:
    out: list[SensorEntityDescription] = [
        SensorEntityDescription(key="overview", name="CCMS STATUS"),
        SensorEntityDescription(key="billing_history", name="LAST BILLING MONTH"),
        SensorEntityDescription(key="bill_due_date", name="DUE DATE"),
        SensorEntityDescription(key="meter_read_date", name="READING DATE"),
        SensorEntityDescription(key="issue_date", name="ISSUE DATE"),
    ]
    for key, name, unit, prec in [
        ("hist_latest_units_kwh", "REMAINING UNITS", "kWh", 3),
        ("hist_latest_payment_pkr", "LAST BILLING MONTH COST", "PKR", 0),
        ("imp_offpeak_units", "CURRENT IMP(O) UNITS", "kWh", 3),
        ("imp_peak_units", "CURRENT IMP(P) UNITS", "kWh", 3),
        ("exp_offpeak_units", "CURRENT EXP(O) UNITS", "kWh", 3),
        ("exp_peak_units", "CURRENT EXP(P) UNITS", "kWh", 3),
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
            return "OK" if self.coordinator.last_update_success else "ERROR"

        if key == "billing_history":
            m = data.get("hist_latest_month")
            return str(m).upper() if m else None

        if key in _STRING_VALUE_KEYS:
            raw = data.get(key)
            if raw is None or str(raw).strip() == "":
                return None
            return str(raw).strip()

        raw = data.get(key)
        if raw is None or raw == "":
            return None
        return _to_float(raw)

    @property
    def extra_state_attributes(self) -> dict:
        """Overview: bill context. LAST BILLING MONTH: full history table."""
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
