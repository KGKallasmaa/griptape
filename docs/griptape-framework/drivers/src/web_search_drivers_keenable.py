import os

from griptape.drivers.web_search.keenable import KeenableWebSearchDriver

# The API key is optional; without one the keyless public endpoint is used (rate-limited per IP).
driver = KeenableWebSearchDriver(api_key=os.environ.get("KEENABLE_API_KEY"))

driver.search("griptape ai")
