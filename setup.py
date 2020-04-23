from setuptools import setup, find_packages
import re
from pathlib import Path

PACKAGE_NAME = "covid19_forecaster"
HERE = Path(__file__).parent.absolute()


def find_version(*paths: str) -> str:
    with HERE.joinpath(*paths).open("tr") as fp:
        version_file = fp.read()
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


DESCRIPTION = (
    "Forecasting the revenue impact of COVID-19"
    " on the City of Philadelphia's finances"
)

setup(
    name=PACKAGE_NAME,
    version=find_version(PACKAGE_NAME, "__init__.py"),
    author="Nick Hand",
    maintainer="Nick Hand",
    maintainer_email="nick.hand@phila.gov",
    packages=find_packages(),
    description=DESCRIPTION,
    license="MIT",
    python_requires=">=3.6",
    install_requires=[
        "pandas",
        "fbprophet",
        "phila-style",
        "matplotlib",
        "openpyxl",
    ],
)
