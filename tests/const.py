"""Shared test constants and mock data."""

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.moixa.coordinator import MoixaData

MOCK_SITE_ID = "site-b9795c8b-cc0e-498a-b87c-ac32a501a273"
MOCK_BATTERY_DEVICE_ID = "229b540a-a47a-4d56-a437-ac1140dedcb8"

MOCK_CONFIG = {
    CONF_USERNAME: "test@example.com",
    CONF_PASSWORD: "testpassword",
}

MOCK_SITE_USERS = [
    {
        "username": "customer:mock-uuid",
        "siteId": MOCK_SITE_ID,
        "vendor": "moixa",
        "devices": [
            {
                "deviceType": "VirtualMoixaGridShareHub",
                "id": "3c363fc3-b76a-4488-b9f4-53f9ea93acaa",
                "mac": "moixa__hub-v2-mock",
            },
            {
                "deviceType": "VirtualMoixaVictronSmartBattery",
                "id": MOCK_BATTERY_DEVICE_ID,
                "mac": "moixa__smartbatteryv4-v1-mock",
            },
        ],
    }
]

# Realistic JTS response matching the live API shape.
MOCK_CORE_READINGS = {
    "docType": "jts",
    "version": "v1",
    "header": {
        "startTime": "latest",
        "endTime": "latest",
        "recordCount": 1,
        "columns": {
            "0": {"id": "groupId", "name": "groupId"},
            "1": {"id": "core/consumption/in/AC/W", "name": "core/consumption/in/AC/W"},
            "2": {"id": "core/grid/in/AC/W", "name": "core/grid/in/AC/W"},
            "3": {"id": "core/grid/out/AC/W", "name": "core/grid/out/AC/W"},
            "4": {"id": "core/production/out/AC/W", "name": "core/production/out/AC/W"},
            "5": {"id": "core/storage/in/AC/W", "name": "core/storage/in/AC/W"},
            "6": {"id": "core/storage/out/AC/W", "name": "core/storage/out/AC/W"},
        },
    },
    "data": [
        {
            "ts": "2026-05-10T12:09:47.848Z",
            "f": {
                "1": {"v": 489.6},
                "2": {"v": 0.0},
                "3": {"v": 1751.7},
                "4": {"v": 722.0},
                "5": {"v": 1984.1},
                "6": {"v": 0.0},
            },
        }
    ],
}

MOCK_MOIXA_DATA = MoixaData(
    battery_soc=85.0,
    consumption_w=489.6,
    grid_import_w=0.0,
    grid_export_w=1751.7,
    solar_w=722.0,
    battery_charging_w=1984.1,
    battery_discharging_w=0.0,
)
