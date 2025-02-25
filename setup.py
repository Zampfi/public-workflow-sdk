from setuptools import setup, find_packages

setup(
    name="zamp_public_workflow_sdk",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic",
        "temporalio",
    ],
)