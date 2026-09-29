"""
Setup configuration for Orvix Sphere.
Allows editable development installs (`pip install -e .`) and standard packaging.
"""

from setuptools import setup, find_packages

setup(
    name="orvix-sphere",
    version="8.0.0",
    description="Orvix Sphere: Autonomous Cognitive Intelligence & Physical AI Framework",
    author="Orvix Engineering Team",
    packages=find_packages(exclude=[
        "tests*", "docs*", "scratch*", "logs*", "data_backups*",
        "checkpoints*", "exported_model*", "dist*", "build*"
    ]),
    py_modules=["phass_cli", "orvix_cli", "auto_install", "install_phass_service"],
    entry_points={
        "console_scripts": [
            "orvix=phass_cli:main",
            "orvix-web=web.launcher:main",
        ],
    },
    include_package_data=True,
    python_requires=">=3.10",
)
