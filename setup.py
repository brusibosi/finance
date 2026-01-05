"""
Setup configuration for finance package.

Installs under the aletrader.finance namespace.
"""

from setuptools import setup, find_packages


setup(
    name="aletrader-finance",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
)
