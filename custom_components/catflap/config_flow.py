import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_ACTIVITY_WINDOW_SECONDS,
    CONF_CHIP_ID,
    CONF_EVENT_DEDUPE_SECONDS,
    CONF_INSIDE,
    CONF_NAME,
    CONF_NEW_CHIP_ID,
    CONF_OLD_CHIP_ID,
    DATA_HUB,
    DEFAULT_ACTIVITY_WINDOW_SECONDS,
    DEFAULT_EVENT_DEDUPE_SECONDS,
    DOMAIN,
)
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
            menu_options=["add_cat", "edit_cat", "remove_cat", "set_presence", "settings"],
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
        options = self._cat_options(hub)
        if not options:
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
                        SelectSelectorConfig(options=options)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_set_presence(self, user_input=None) -> FlowResult:
        hub = self._get_hub()
        options = self._cat_options(hub)
        if not options:
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
                        SelectSelectorConfig(options=options)
                    ),
                    vol.Required(CONF_INSIDE): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_edit_cat(self, user_input=None) -> FlowResult:
        hub = self._get_hub()
        options = self._cat_options(hub)
        if not options:
            return self.async_abort(reason="no_cats_registered")

        if user_input is not None:
            selected_chip = user_input[CONF_OLD_CHIP_ID]
            return await self.async_step_edit_cat_details(
                {CONF_OLD_CHIP_ID: selected_chip}
            )

        return self.async_show_form(
            step_id="edit_cat",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OLD_CHIP_ID): SelectSelector(
                        SelectSelectorConfig(options=options)
                    ),
                }
            ),
        )

    async def async_step_edit_cat_details(self, user_input=None) -> FlowResult:
        hub = self._get_hub()
        errors = {}

        if user_input is not None and CONF_OLD_CHIP_ID in user_input and len(user_input) == 1:
            old_chip_id = user_input[CONF_OLD_CHIP_ID]
            cat = hub.cats.get(old_chip_id)
            if not cat:
                return self.async_abort(reason="unknown_chip_id")
            return self.async_show_form(
                step_id="edit_cat_details",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_OLD_CHIP_ID, default=old_chip_id): str,
                        vol.Required(CONF_NEW_CHIP_ID, default=old_chip_id): str,
                        vol.Required(CONF_NAME, default=cat.name): str,
                        vol.Required(CONF_INSIDE, default=cat.inside): bool,
                    }
                ),
            )

        if user_input is not None:
            updated = await hub.async_update_cat(
                old_chip_id=user_input[CONF_OLD_CHIP_ID],
                new_chip_id=user_input[CONF_NEW_CHIP_ID],
                name=user_input[CONF_NAME],
                inside=user_input[CONF_INSIDE],
            )
            if updated:
                return self.async_create_entry(title="", data={})
            errors["base"] = "cat_update_failed"

        return self.async_show_form(
            step_id="edit_cat_details",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OLD_CHIP_ID): str,
                    vol.Required(CONF_NEW_CHIP_ID): str,
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_INSIDE): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_settings(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=self._with_options(user_input))

        current = self._current_options()
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EVENT_DEDUPE_SECONDS,
                        default=current[CONF_EVENT_DEDUPE_SECONDS],
                    ): NumberSelector(
                        NumberSelectorConfig(min=0, max=30, step=1, mode=NumberSelectorMode.BOX)
                    ),
                    vol.Required(
                        CONF_ACTIVITY_WINDOW_SECONDS,
                        default=current[CONF_ACTIVITY_WINDOW_SECONDS],
                    ): NumberSelector(
                        NumberSelectorConfig(min=5, max=120, step=1, mode=NumberSelectorMode.BOX)
                    ),
                }
            ),
        )

    def _get_hub(self) -> CatFlapHub:
        bucket = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if not bucket:
            raise HomeAssistantError("Cat flap entry is not loaded")
        return bucket[DATA_HUB]

    @staticmethod
    def _cat_options(hub: CatFlapHub) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        for chip_id in sorted(hub.cats.keys()):
            cat = hub.cats[chip_id]
            options.append(
                {
                    "value": chip_id,
                    "label": f"{cat.name} ({chip_id})",
                }
            )
        return options

    def _current_options(self) -> dict[str, int]:
        options = self._config_entry.options
        return {
            CONF_EVENT_DEDUPE_SECONDS: int(
                options.get(CONF_EVENT_DEDUPE_SECONDS, DEFAULT_EVENT_DEDUPE_SECONDS)
            ),
            CONF_ACTIVITY_WINDOW_SECONDS: int(
                options.get(CONF_ACTIVITY_WINDOW_SECONDS, DEFAULT_ACTIVITY_WINDOW_SECONDS)
            ),
        }

    def _with_options(self, updates: dict) -> dict:
        merged = dict(self._config_entry.options)
        merged.update(updates)
        return merged
