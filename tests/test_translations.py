"""Tests for the translated entity and service names."""

import json
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)

from custom_components.phoniebox.const import (
    BINARY_SWITCHES,
    BOOLEAN_SENSORS,
    BUTTON_TRANSLATION_KEYS,
    DOMAIN,
    GIGABYTE_SENSORS,
    STRING_SENSORS,
    TOPIC_DOMAIN_TEMPERATUR,
)
from custom_components.phoniebox.utils import translation_key

from .const import MOCK_CONFIG

COMPONENT = Path(__file__).parent.parent / "custom_components" / DOMAIN
LANGUAGES = ("en", "de")


def _load(language: str) -> dict:
    return json.loads((COMPONENT / "translations" / f"{language}.json").read_text())


def _keys(data: dict, prefix: str = "") -> set[str]:
    keys = set()
    for key, value in data.items():
        path = f"{prefix}{key}"
        keys.add(path)
        if isinstance(value, dict):
            keys |= _keys(value, f"{path}.")
    return keys


def test_languages_have_the_same_keys() -> None:
    """German and English cover exactly the same texts."""
    assert _keys(_load("de")) == _keys(_load("en"))


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_entity_has_a_name(language: str) -> None:
    """Every translation key the platforms use has a name."""
    entity = _load(language)["entity"]
    expected = {
        "button": set(BUTTON_TRANSLATION_KEYS.values()),
        "binary_sensor": {translation_key(name) for name in BOOLEAN_SENSORS},
        "switch": {translation_key(name) for name in BINARY_SWITCHES},
        "sensor": {
            translation_key(name)
            for name in [
                *STRING_SENSORS,
                *GIGABYTE_SENSORS,
                TOPIC_DOMAIN_TEMPERATUR,
                "state",
                "player state",
                "source",
            ]
        },
    }
    for platform, keys in expected.items():
        assert keys <= set(entity[platform]), platform
        for key in keys:
            assert entity[platform][key]["name"], f"{platform}.{key}"


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_service_is_translated(language: str) -> None:
    """Each service and each of its fields has a name and description."""
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    translated = _load(language)["services"]
    assert set(translated) == set(services)
    for service, definition in services.items():
        assert translated[service]["name"]
        assert translated[service]["description"]
        fields = translated[service].get("fields", {})
        assert set(fields) == set(definition.get("fields", {})), service
        for field in fields.values():
            assert field["name"]
            assert field["description"]


async def _setup(hass: HomeAssistant, language: str) -> None:
    hass.config.language = language
    entry = MockConfigEntry(
        title="Phoniebox Test",
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id=MOCK_CONFIG["phoniebox_name"],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    async_fire_mqtt_message(hass, "test_phoniebox/attribute/disk_avail", "12")
    async_fire_mqtt_message(hass, "test_phoniebox/attribute/rfid", "true")
    await hass.async_block_till_done()


def _name(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    assert state is not None, entity_id
    return state.attributes["friendly_name"]


@pytest.mark.parametrize(
    ("language", "names"),
    [
        (
            "de",
            {
                "media_player.phoniebox_test_box": "Phoniebox test_box",
                "button.phoniebox_test_box_restart_phoniebox": (
                    "Phoniebox test_box Neu starten"
                ),
                "sensor.phoniebox_test_box_disk_avail": (
                    "Phoniebox test_box Freier Speicher"
                ),
                "switch.phoniebox_test_box_rfid": "Phoniebox test_box RFID-Leser",
                "binary_sensor.phoniebox_test_box_rfid": (
                    "Phoniebox test_box RFID-Leser"
                ),
            },
        ),
        (
            "en",
            {
                "media_player.phoniebox_test_box": "Phoniebox test_box",
                "button.phoniebox_test_box_restart_phoniebox": (
                    "Phoniebox test_box Restart"
                ),
                "sensor.phoniebox_test_box_disk_avail": (
                    "Phoniebox test_box Disk available"
                ),
                "switch.phoniebox_test_box_rfid": "Phoniebox test_box RFID reader",
                "binary_sensor.phoniebox_test_box_rfid": (
                    "Phoniebox test_box RFID reader"
                ),
            },
        ),
    ],
)
async def test_names_follow_the_language(
    hass: HomeAssistant, language: str, names: dict[str, str]
) -> None:
    """Names follow the language of HA, entity IDs stay as before."""
    await _setup(hass, language)
    for entity_id, name in names.items():
        assert _name(hass, entity_id) == name
