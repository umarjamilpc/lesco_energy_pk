"""Constants for LESCO integration."""

from datetime import timedelta

DOMAIN = "lesco"

CONF_REFERENCE = "reference"

DEFAULT_UPDATE_INTERVAL = timedelta(hours=6)

CCMS_BILL_URL = "https://ccms.pitc.com.pk/api/details/bill"
