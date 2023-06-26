#!/usr/bin/env python3

from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="madata",
    version='0.2.0',
    author="Renat Shigapov",
    license="MIT",
    description="A tool for syncing the dataset-metadata between MADATA and Wikidata",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UB-Mannheim/madata",
    install_requires=['sickle', 'pandas', 'requests', 'wikidataintegrator', 'tqdm', 'appengine-python-standard'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
