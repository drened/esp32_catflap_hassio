import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import CONF_CHIP_ID, CONF_INSIDE, CONF_NAME, DATA_HUB, DOMAIN
from .hub import CatFlapHub


class CatFlapConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        await self.async_set_unique_id("catflap")
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return CatFlapOptionsFlow(config_entry)


class CatFlapOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_cat", "remove_cat", "set_presence"],
        )

    async def async_step_add_cat(self, user_input=None) -> FlowResult:
        if user_input is not None:
            hub = self._get_hub()
            await hub.async_register_cat(
                chip_id=user_input[CONF_CHIP_ID],
                name=user_input[CONF_NAME],
                inside=user_input[CONF_INSIDE],
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_cat",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHIP_ID): str,
                    vol.Required(CONF_NAME): str,
                    vol.Optional(CONF_INSIDE, default=False): bool,
                }
            ),
        )

    async def async_step_remove_cat(self, user_input=None) -> FlowResult:
        hub = self._get_hub()
        chip_ids = sorted(hub.cats.keys())
        if not chip_ids:
            return self.async_abort(reason="no_cats_registered")

        errors = {}
        if user_input is not None:
            removed = await hub.async_remove_cat(user_input[CONF_CHIP_ID])
            if removed:
                return self.async_create_entry(title="", data={})
            errors["base"] = "unknown_chip_id"

        return self.async_show_form(
            step_id="remove_cat",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHIP_ID): SelectSelector(
                        SelectSelectorConfig(options=chip_ids)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_set_presence(self, user_input=None) -> FlowResult:
        hub = self._get_hub()
        chip_ids = sorted(hub.cats.keys())
        if not chip_ids:
            return self.async_abort(reason="no_cats_registered")

        errors = {}
        if user_input is not None:
            updated = await hub.async_set_presence(
                chip_id=user_input[CONF_CHIP_ID],
                inside=user_input[CONF_INSIDE],
            )
            if updated:
                return self.async_create_entry(title="", data={})
            errors["base"] = "unknown_chip_id"

        return self.async_show_form(
            step_id="set_presence",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHIP_ID): SelectSelector(
                        SelectSelectorConfig(options=chip_ids)
                    ),
                    vol.Required(CONF_INSIDE): bool,
                }
            ),
            errors=errors,
        )

    def _get_hub(self) -> CatFlapHub:
        bucket = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if not bucket:
            raise HomeAssistantError("Cat flap entry is not loaded")
        return bucket[DATA_HUB]
