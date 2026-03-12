DOMAIN = "catflap"

CONF_NAME = "name"
CONF_CHIP_ID = "chip_id"
CONF_ENTRY_ID = "entry_id"
CONF_DIRECTION = "direction"
CONF_INSIDE = "inside"
CONF_SOURCE = "source"

DATA_CATS = "cats"
DATA_FLAP = "flap"
DATA_HUB = "hub"

PLATFORMS = ["binary_sensor", "sensor"]

SERVICE_PROCESS_EVENT = "process_event"
SERVICE_REGISTER_CAT = "register_cat"
SERVICE_REMOVE_CAT = "remove_cat"
SERVICE_SET_PRESENCE = "set_presence"

ATTR_CAT_NAME = "cat_name"
ATTR_KNOWN_CAT = "known_cat"

DIRECTION_IN = "in"
DIRECTION_OUT = "out"
DIRECTION_UNKNOWN = "unknown"

VALID_DIRECTIONS = {DIRECTION_IN, DIRECTION_OUT, DIRECTION_UNKNOWN}
