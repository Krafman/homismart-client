"""Packaging for homismart-client. The version comes from homismart_client/__init__.py."""
import re
from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).parent
VERSION = re.search(
    r"""__version__ = ["']([^"']+)["']""",
    (HERE / "homismart_client" / "__init__.py").read_text(encoding="utf-8"),
).group(1)

setup(
    name="homismart-client",
    version=VERSION,
    author="Adir Krafman",
    author_email="adirkrafman@gmail.com",
    description="Unofficial asyncio client for the Homismart smart home WebSocket API",
    long_description=(HERE / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/krafman/homismart-client",
    project_urls={
        "Bug Tracker": "https://github.com/krafman/homismart-client/issues",
        "Changelog": "https://github.com/krafman/homismart-client/blob/main/CHANGELOG.md",
        "Home Assistant integration": "https://github.com/Krafman/ha-homismart",
    },
    license="MIT",
    packages=find_packages(exclude=["tests*", "examples*"]),
    install_requires=["websockets>=13.0"],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Operating System :: OS Independent",
        "Topic :: Home Automation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="homismart, smart home, websocket, iot, home automation, home assistant",
)
