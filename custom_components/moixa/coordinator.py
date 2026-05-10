"""DataUpdateCoordinator for the Moixa integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

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


class MoixaCoordinator(DataUpdateCoordinator[MoixaData]):
    """Polls the Moixa GridShare API on a fixed interval."""

    site_id: str

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
        """Synchronous: authenticate, create client, resolve site ID."""
        tokens = MoixaCognitoAuth(self._username, self._password).login()
        # MoixaClient.__init__ calls boto3 to exchange tokens for AWS creds.
        client = MoixaClient(tokens)
        site_users = client.get_site_users()
        if not site_users:
            raise MoixaError("No sites found for this account")
        entry = site_users[0]
        self.site_id = entry["siteId"]
        # Pre-populate the client's internal cache so get_current_battery_level()
        # skips the redundant get_site_users() call it would otherwise make.
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
            if err.response is not None and err.response.status_code == 401:
                raise ConfigEntryAuthFailed("Session expired, please re-authenticate") from err
            raise UpdateFailed(f"HTTP error from Moixa API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Moixa API: {err}") from err

    def _fetch(self) -> MoixaData:
        """Synchronous: call both API endpoints and combine results."""
        assert self._client is not None
        readings = self._client.get_core_readings(self.site_id)
        parsed = _parse_core_readings(readings)
        soc_raw = self._client.get_current_battery_level()
        # API returns SOC as a fraction (0.0-1.0); convert to percent (0-100).
        soc = round(soc_raw * 100, 1) if soc_raw >= 0 else None
        return MoixaData(battery_soc=soc, **parsed)
