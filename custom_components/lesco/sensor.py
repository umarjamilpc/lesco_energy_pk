"""Sensors for LESCO overview and numeric billing helpers."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REFERENCE, DOMAIN
from .coordinator import LescoCoordinator

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="overview",
        name="Overview",
    ),
    SensorEntityDescription(
        key="net_bill",
        name="Net bill",
        native_unit_of_measurement="PKR",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="curr_amount_due",
        name="Current amount due",
        native_unit_of_measurement="PKR",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="tot_cur_cons",
        name="Billed month total consumption",
        native_unit_of_measurement="kWh",
        suggested_display_precision=3,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Add sensors."""
    coordinator: LescoCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[LescoSensor] = [LescoSensor(coordinator, desc) for desc in SENSORS]
    async_add_entities(entities)


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
    def native_value(self) -> str | float | None:
        """State value."""
        if self.coordinator.data is None:
            return None
        if self.entity_description.key == "overview":
            return "ok" if self.coordinator.last_update_success else "error"

        key = self.entity_description.key
        if key not in ("net_bill", "curr_amount_due", "tot_cur_cons"):
            return None
        raw = self.coordinator.data.get(key)
        if raw is None or raw == "":
            return None
        cleaned = str(raw).replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict:
        """Attach full coordinator payload to overview sensor only."""
        if self.entity_description.key != "overview":
            return {}
        if not self.coordinator.data:
            return {}
        data = dict(self.coordinator.data)
        # Do not duplicate huge raw in every sensor; keep on overview
        return {k: v for k, v in data.items() if v is not None}
