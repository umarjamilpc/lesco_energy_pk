"""Constants for LESCO integration."""

from datetime import timedelta

DOMAIN = "lesco"

CONF_PHONE = "phone"
CONF_PASSWORD = "password"
CONF_REFERENCE = "reference"

DEFAULT_UPDATE_INTERVAL = timedelta(hours=6)

POWERSMART_BASE = "https://api-powersmart.pitc.com.pk"
CCMS_BILL_URL = "https://ccms.pitc.com.pk/api/details/bill"
