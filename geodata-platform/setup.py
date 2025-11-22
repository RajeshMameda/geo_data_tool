# In /Users/rajeshmameda/geodata-platform/setup.py
from setuptools import setup, find_packages

setup(
    name="geodata_platform",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "azure-functions",
        "pydantic",
        "sqlalchemy",
        "psycopg2-binary",
        "python-dotenv",
        # Add other dependencies as needed
    ],
)