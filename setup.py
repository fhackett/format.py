from setuptools import setup, find_packages

setup(
    name="format",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "bitstring",
        "pytest-asyncio",
        "pytest-catchlog",
    ],
    entry_points={}
)
