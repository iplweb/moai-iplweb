import sys
import os
import site
import tempfile
from configparser import ConfigParser, NoSectionError
from logging.config import fileConfig

os.environ["PYTHON_EGG_CACHE"] = tempfile.mkdtemp(prefix="moai-egg-cache-")

site.addsitedir(
    os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        "lib",
        "python%d.%d" % sys.version_info[:2],
        "site-packages",
    )
)

from paste.deploy import loadapp  # noqa: E402

config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)), "settings.ini")
try:
    fileConfig(config_file)
except NoSectionError:
    pass  # no logging configured

application = loadapp("config:%s" % config_file)
