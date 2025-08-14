from setuptools import setup, find_packages

setup(
    name="health-ai-search",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "pytest-asyncio",
        "pytest-mock",
        "pymongo",
        "bson"
    ],
) 