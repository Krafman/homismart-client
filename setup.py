# setup.py

import os
import re
from setuptools import setup, find_packages

def get_version(package_name):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    init_py = open(os.path.join(here, package_name, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)

def get_long_description():
    """
    Return the README.md.
    """
    # When we create README.md, its content will be used here.
    # For now, a placeholder or the short description can be used.
    if os.path.exists("README.md"):
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    return "A Python client for interacting with Homismart devices via their WebSocket API."

version = get_version("homismart_client") # Assumes your package directory is 'homismart_client'

setup(
    name="homismart-client",
    version=version,
    author="Adir Krafman", # Replace with your name or alias
    author_email="adirkrafman@gmail.com", # Replace with your email
    description="Python client for Homismart WebSocket API",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/krafman/homismart-client", # Replace with your project's URL
    project_urls={
        "Bug Tracker": "https://github.com/krafman/homismart-client/issues", # Replace
    },
    license="MIT",  # Or choose another license like Apache 2.0, etc.
    packages=find_packages(exclude=['tests*', 'examples*']),
    # Ensure 'homismart_client' and 'homismart_client.devices' are found
    # find_packages() should handle this if your structure is:
    # HomiSmart Client/
    # ├── setup.py
    # └── homismart_client/
    #     ├── __init__.py
    #     └── devices/
    #         └── __init__.py
    #     └── ... (other .py files)

    install_requires=[
        "websockets>=10.0",
        "python-dotenv>=1.0.0", # Specify a version range for the websockets library
                            # Check latest stable, e.g., >=10.0, <13.0
    ],
    python_requires=">=3.8", # Based on asyncio features and type hinting
    classifiers=[
        "Development Status :: 3 - Alpha",  # Or "4 - Beta" / "5 - Production/Stable"
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License", # Change if you chose a different license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Home Automation",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="homismart, smart home, websocket, iot, home automation",
    # If you have entry points for command-line scripts (not typical for this library)
    # entry_points={
    #     "console_scripts": [
    #         "homismart-cli=homismart_client.cli:main",
    #     ],
    # },
)