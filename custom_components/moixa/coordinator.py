"""DataUpdateCoordinator for the Moixa integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from requests import HTTPError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .moixa_py import MoixaCognitoAuth, MoixaClient
from .moixa_py.exceptions import MoixaAuthError, MoixaError

_LOGGER = logging.getLogger(__name__)


@dataclass
class MoixaData:
    """Snapshot of all sensor values from one coordinator refresh."""

    battery_soc: float | None
    consumption_w: float | None
    grid_import_w: float | None
    grid_export_w: float | None
    solar_w: float | None
    battery_charging_w: float | None
    battery_discharging_w: float | None
    operation_mode: str | None
    # 24-hour forecast: list of {ts, consumption_W, production_W} dicts, 30-min slots
    forecasts: list[dict] | None = field(default=None)
    # Weekly schedule plan from get_device_operation_schedule
    schedule: dict | None = field(default=None)
    # 24-hour intent time series: list of {startTime, endTime, intent} dicts
    intent_series: list[dict] | None = field(default=None)


def _parse_core_readings(readings: dict) -> dict[str, float | None]:
    """Extract per-channel watt values from a JTS coreReadingsV3 response.

    The response header maps column indices (string keys) to channel IDs.
    Data rows use those same indices under the 'f' key.
    """
    columns: dict[str, dict] = readings.get("header", {}).get("columns", {})
    col_map: dict[str, str] = {info["id"]: idx for idx, info in columns.items()}

    rows = readings.get("data", [])
    if not rows:
        return {}

    fields: dict[str, dict] = rows[0].get("f", {})

    def _v(channel: str) -> float | None:
        idx = col_map.get(channel)
        if idx is None:
            return None
        raw = fields.get(idx, {}).get("v")
        return float(raw) if raw is not None else None

    return {
        "consumption_w": _v("core/consumption/in/AC/W"),
        "grid_import_w": _v("core/grid/in/AC/W"),
        "grid_export_w": _v("core/grid/out/AC/W"),
        "solar_w": _v("core/production/out/AC/W"),
        "battery_charging_w": _v("core/storage/in/AC/W"),
        "battery_discharging_w": _v("core/storage/out/AC/W"),
    }


def _parse_soc(status: dict) -> float | None:
    """Extract battery SOC (as %) from a JTS specificReadings response."""
    columns: dict[str, dict] = status.get("header", {}).get("columns", {})
    soc_col = next(
        (k for k, v in columns.items() if v.get("id") == "storage/SOC"),
        None,
    )
    if soc_col is None:
        return None
    raw = status.get("data", [{}])[0].get("f", {}).get(soc_col, {}).get("v")
    if raw is None:
        return None
    # API returns SOC as a fraction (0.0-1.0); convert to percent.
    return round(float(raw) * 100, 1)


class MoixaCoordinator(DataUpdateCoordinator[MoixaData]):
    """Polls the Moixa GridShare API on a fixed interval."""

    site_id: str
    battery_device_id: str

    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._client: MoixaClient | None = None
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_setup(self) -> None:
        """Authenticate and discover site/device IDs (called once before first fetch)."""
        try:
            await self.hass.async_add_executor_job(self._login_and_discover)
        except MoixaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Moixa setup failed: {err}") from err

    def _login_and_discover(self) -> None:
        """Synchronous: authenticate, create client, resolve site and battery device IDs."""
        tokens = MoixaCognitoAuth(self._username, self._password).login()
        client = MoixaClient(tokens)
        site_users = client.get_site_users()
        if not site_users:
            raise MoixaError("No sites found for this account")
        entry = site_users[0]
        self.site_id = entry["siteId"]
        battery_id = next(
            (
                d["id"]
                for d in entry.get("devices", [])
                if d.get("deviceType") == "VirtualMoixaVictronSmartBattery"
            ),
            None,
        )
        if battery_id is None:
            raise MoixaError("No battery device found for this account")
        self.battery_device_id = battery_id
        client.known_site_users = site_users
        self._client = client

    async def _async_update_data(self) -> MoixaData:
        """Fetch the latest readings from the API."""
        assert self._client is not None
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except MoixaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except HTTPError as err:
            if err.response is not None and err.response.status_code in (401, 403):
                _LOGGER.debug("Got %s, attempting full re-login", err.response.status_code)
                try:
                    await self.hass.async_add_executor_job(self._login_and_discover)
                    return await self.hass.async_add_executor_job(self._fetch)
                except MoixaAuthError as reauth_err:
                    raise ConfigEntryAuthFailed(str(reauth_err)) from reauth_err
                except Exception as reauth_err:
                    raise UpdateFailed(f"Re-login failed: {reauth_err}") from reauth_err
            raise UpdateFailed(f"HTTP error from Moixa API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Moixa API: {err}") from err

    def _fetch(self) -> MoixaData:
        """Synchronous: call API endpoints and combine results."""
        assert self._client is not None
        readings = self._client.get_core_readings(self.site_id)
        parsed = _parse_core_readings(readings)
        status = self._client.get_device_status(self.battery_device_id)
        soc = _parse_soc(status)
        mode_resp = self._client.get_device_current_operation_mode(self.battery_device_id)
        operation_mode = mode_resp.get("mode") if isinstance(mode_resp, dict) else None
        now = datetime.now(timezone.utc)
        start = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        forecasts: list[dict] | None = None
        try:
            forecasts = MoixaClient.parse_jts(
                self._client.get_site_forecasts(self.site_id, start, end)
            )
        except Exception:
            _LOGGER.debug("Forecast fetch failed", exc_info=True)

        schedule: dict | None = None
        try:
            schedule = self._client.get_device_operation_schedule(self.battery_device_id).get("plan")
        except Exception:
            _LOGGER.debug("Schedule fetch failed", exc_info=True)

        intent_series: list[dict] | None = None
        try:
            resp = self._client.get_device_intent_time_series(self.battery_device_id, start, end)
            intent_series = resp.get("timeSeries")
        except Exception:
            _LOGGER.debug("Intent time series fetch failed", exc_info=True)

        return MoixaData(
            battery_soc=soc,
            operation_mode=operation_mode,
            forecasts=forecasts,
            schedule=schedule,
            intent_series=intent_series,
            **parsed,
        )

    async def async_set_operation_mode(self, mode: str) -> None:
        """Set the battery operation mode and refresh coordinator data."""
        assert self._client is not None
        await self.hass.async_add_executor_job(
            self._client.set_device_operation_mode, self.battery_device_id, mode
        )
        await self.async_request_refresh()

    async def async_add_schedule_intent(
        self,
        kind: str,
        duration_minutes: int,
        position: int = -1,
        soc_min: float = 0.1,
        soc_max: float = 1.0,
        power_watts: float | None = None,
    ) -> None:
        """Insert a new intent slot into the weekly schedule."""
        assert self._client is not None
        await self.hass.async_add_executor_job(
            lambda: self._client.add_schedule_intent(
                self.battery_device_id,
                kind,
                duration_minutes,
                position=position,
                soc_min=soc_min,
                soc_max=soc_max,
                power_watts=power_watts,
            )
        )
        await self.async_request_refresh()

    async def async_remove_schedule_slot(self, index: int) -> None:
        """Remove an intent slot from the weekly schedule by index."""
        assert self._client is not None
        await self.hass.async_add_executor_job(
            self._client.delete_schedule_intent, self.battery_device_id, index
        )
        await self.async_request_refresh()
