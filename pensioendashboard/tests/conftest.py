# add this in the conftest.py under tests folder
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import os
from pathlib import Path


# in case the environment variables are not loaded. These are stored
# at ../.. location in my development environment
DIRPATH = Path(os.path.dirname(__file__)).parent.parent
ENVLOCATION = os.path.join(DIRPATH, ".env")

try:
    load_dotenv(dotenv_path=ENVLOCATION)

    print("Succesfully loaded environment variables from {}".format(
        ENVLOCATION))
except Exception as e:
    print("Error while loading environment variables. "
          "Might lead to errors furtheron.\n"
          "Error message: {}".format(e))


def pytest_setup_options():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    return options
