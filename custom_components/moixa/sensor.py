"""Sensor platform for the Moixa integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MoixaCoordinator, MoixaData


def _device_info(coordinator: MoixaCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.site_id)},
        name="Moixa GridShare",
        manufacturer="Moixa",
        model="Smart Battery",
    )


@dataclass(frozen=True, kw_only=True)
class MoixaSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a typed value extractor."""

    value_fn: Callable[[MoixaData], float | None]


_SENSOR_DESCRIPTIONS: tuple[MoixaSensorEntityDescription, ...] = (
    MoixaSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda d: d.battery_soc,
    ),
    MoixaSensorEntityDescription(
        key="home_consumption",
        translation_key="home_consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.consumption_w,
    ),
    MoixaSensorEntityDescription(
        key="grid_import",
        translation_key="grid_import",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.grid_import_w,
    ),
    MoixaSensorEntityDescription(
        key="grid_export",
        translation_key="grid_export",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.grid_export_w,
    ),
    MoixaSensorEntityDescription(
        key="solar_production",
        translation_key="solar_production",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.solar_w,
    ),
    MoixaSensorEntityDescription(
        key="battery_charging",
        translation_key="battery_charging",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.battery_charging_w,
    ),
    MoixaSensorEntityDescription(
        key="battery_discharging",
        translation_key="battery_discharging",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=lambda d: d.battery_discharging_w,
    ),
)


@dataclass(frozen=True, kw_only=True)
class MoixaForecastSensorDescription(SensorEntityDescription):
    """Sensor description for 24-hour forecast sensors."""

    value_key: str  # key in the JTS row dict: "consumption_W" or "production_W"


_FORECAST_DESCRIPTIONS: tuple[MoixaForecastSensorDescription, ...] = (
    MoixaForecastSensorDescription(
        key="forecast_consumption",
        translation_key="forecast_consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_key="consumption_W",
    ),
    MoixaForecastSensorDescription(
        key="forecast_solar",
        translation_key="forecast_solar",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_key="production_W",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Moixa sensors from a config entry."""
    coordinator: MoixaCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        MoixaSensor(coordinator, description) for description in _SENSOR_DESCRIPTIONS
    ]
    entities += [
        MoixaForecastSensor(coordinator, description)
        for description in _FORECAST_DESCRIPTIONS
    ]
    async_add_entities(entities)


class MoixaSensor(CoordinatorEntity[MoixaCoordinator], SensorEntity):
    """A single Moixa sensor backed by the coordinator."""

    _attr_has_entity_name = True
    entity_description: MoixaSensorEntityDescription

    def __init__(
        self,
        coordinator: MoixaCoordinator,
        description: MoixaSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.site_id}_{description.key}"
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class MoixaForecastSensor(CoordinatorEntity[MoixaCoordinator], SensorEntity):
    """Forecast sensor: state = next 30-min slot, attribute = full 24h series."""

    _attr_has_entity_name = True
    entity_description: MoixaForecastSensorDescription

    def __init__(
        self,
        coordinator: MoixaCoordinator,
        description: MoixaForecastSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.site_id}_{description.key}"
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        forecasts = self._forecasts
        if not forecasts:
            return None
        return forecasts[0].get(self.entity_description.value_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        forecasts = self._forecasts
        if not forecasts:
            return {}
        return {
            "forecast": [
                {"ts": row["ts"], "W": row.get(self.entity_description.value_key)}
                for row in forecasts
            ]
        }

    @property
    def _forecasts(self) -> list[dict] | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.forecasts
