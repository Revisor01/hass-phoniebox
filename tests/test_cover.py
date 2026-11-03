"""Tests for the cover image of the Phoniebox media player."""

from homeassistant.components.media_player import ATTR_ENTITY_PICTURE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_mqtt_message,
)

from custom_components.phoniebox.const import CONF_COVER_URL, DOMAIN
from custom_components.phoniebox.media_player import cover_image_url

from .const import MOCK_CONFIG

ENTITY_ID = "media_player.phoniebox_test_box"
COVER = "http://192.168.0.201/api/cover.php"


async def _setup(hass: HomeAssistant, options: dict) -> MockConfigEntry:
    entry = MockConfigEntry(
        title="Phoniebox Test",
        domain=DOMAIN,
        data=MOCK_CONFIG,
        options=options,
        entry_id=MOCK_CONFIG["phoniebox_name"],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _album(hass: HomeAssistant, album: str) -> None:
    async_fire_mqtt_message(hass, "test_phoniebox/attribute/album", album)
    await hass.async_block_till_done()


def test_cover_image_url() -> None:
    """The album goes into the URL so every album gets its own cache entry."""
    assert cover_image_url(COVER, "Holger in Love") == f"{COVER}?album=Holger+in+Love"
    assert (
        cover_image_url(f"{COVER}?x=1", "Tiger & Co")
        == f"{COVER}?x=1&album=Tiger+%26+Co"
    )
    assert cover_image_url(COVER, None) is None
    assert cover_image_url(COVER, "") is None
    assert cover_image_url(None, "Holger in Love") is None
    assert cover_image_url("", "Holger in Love") is None


async def test_no_picture_without_cover_url(hass: HomeAssistant) -> None:
    """Without a configured address the player shows no picture, as before."""
    await _setup(hass, {})
    await _album(hass, "Holger in Love")

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.attributes.get("media_album_name") == "Holger in Love"
    assert ATTR_ENTITY_PICTURE not in state.attributes


async def test_picture_follows_album(hass: HomeAssistant) -> None:
    """With an address the picture is proxied by HA and changes with the album."""
    await _setup(hass, {CONF_COVER_URL: COVER})

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert ATTR_ENTITY_PICTURE not in state.attributes

    await _album(hass, "Holger in Love")
    first = hass.states.get(ENTITY_ID).attributes[ATTR_ENTITY_PICTURE]
    assert first.startswith(f"/api/media_player_proxy/{ENTITY_ID}?token=")
    assert "192.168.0.201" not in first

    await _album(hass, "Im ungarischen Wald")
    second = hass.states.get(ENTITY_ID).attributes[ATTR_ENTITY_PICTURE]
    assert second != first

    await _album(hass, "Holger in Love")
    assert hass.states.get(ENTITY_ID).attributes[ATTR_ENTITY_PICTURE] == first


async def test_options_flow_sets_cover_url(hass: HomeAssistant) -> None:
    """The address is entered in the options and kept next to other options."""
    entry = await _setup(hass, {"switch": False})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_COVER_URL: COVER}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options == {"switch": False, CONF_COVER_URL: COVER}


async def test_options_flow_rejects_invalid_url(hass: HomeAssistant) -> None:
    """Only http and https addresses are accepted."""
    entry = await _setup(hass, {})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_COVER_URL: "192.168.0.201/api/cover.php"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_COVER_URL: "invalid_url"}
    assert entry.options == {}


async def test_options_flow_clears_cover_url(hass: HomeAssistant) -> None:
    """An empty field removes the address again."""
    entry = await _setup(hass, {CONF_COVER_URL: COVER})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_COVER_URL: ""}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options == {}
