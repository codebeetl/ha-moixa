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

MOCK_DEVICE_STATUS = {
    "docType": "jts",
    "version": "v1",
    "header": {
        "columns": {
            "0": {"id": "storage/SOC", "name": "storage/SOC"},
            "1": {"id": "storage/AC/W", "name": "storage/AC/W"},
        }
    },
    "data": [{"ts": "2026-05-10T12:09:47.848Z", "f": {"0": {"v": 0.85}, "1": {"v": 1984.1}}}],
}

MOCK_OPERATION_MODE = {"mode": "smart"}

MOCK_SCHEDULE = {
    "periodDays": 7,
    "id": "d54c00bc-c619-4953-b545-0eb3e166ff0e",
    "intents": [
        {"intent": {"kind": "balance", "socMin": 0.1, "socMax": 1.0, "powerWattsMin": -20, "powerWattsMax": 20}, "durationMinutes": 2099},
        {"intent": {"kind": "charge/discharge", "socMin": 0.1, "socMax": 1.0, "powerWatts": 2000}, "durationMinutes": 2338},
    ],
}

MOCK_INTENT_SERIES = [
    {
        "startTime": "2026-05-10T19:44:13.000Z",
        "endTime": "2026-05-11T04:30:00.000Z",
        "intent": {"kind": "balance", "socMin": 0.113, "socMax": 1.0, "lowerPowerBand": 0, "upperPowerBand": 1},
    },
    {
        "startTime": "2026-05-11T04:30:00.000Z",
        "endTime": "2026-05-11T05:00:00.000Z",
        "intent": {"kind": "charge/discharge", "socMin": 0.113, "socMax": 0.216, "powerWatts": 2000},
    },
]

MOCK_FORECASTS = [
    {"ts": "2026-05-10T19:30:00.000Z", "consumption_W": 936.1, "production_W": 0.0},
    {"ts": "2026-05-10T20:00:00.000Z", "consumption_W": 899.3, "production_W": 0.0},
    {"ts": "2026-05-11T09:00:00.000Z", "consumption_W": 454.3, "production_W": 858.0},
]

MOCK_MOIXA_DATA = MoixaData(
    battery_soc=85.0,
    consumption_w=489.6,
    grid_import_w=0.0,
    grid_export_w=1751.7,
    solar_w=722.0,
    battery_charging_w=1984.1,
    battery_discharging_w=0.0,
    operation_mode="smart",
    forecasts=MOCK_FORECASTS,
    schedule=MOCK_SCHEDULE,
    intent_series=MOCK_INTENT_SERIES,
)
