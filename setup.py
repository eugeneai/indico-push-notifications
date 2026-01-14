#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup script for Indico Push Notifications Plugin
"""

import os

from setuptools import find_packages, setup

# Read the README file for long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="indico-push-notifications",
    version="1.0.0",
    description="Push notifications plugin for Indico (Telegram and Web Push)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CERN",
    author_email="indico-team@cern.ch",
    url="https://github.com/indico/indico-plugins",
    license="MIT",
    # Package discovery
    packages=find_packages(
        include=["indico_push_notifications", "indico_push_notifications.*"]
    ),
    include_package_data=True,
    zip_safe=False,
    package_dir={"indico_push_notifications": "indico_push_notifications"},
    # Dependencies
    install_requires=requirements,
    # Plugin entry point for Indico
    entry_points={
        "indico.plugins": [
            "indico_push_notifications = indico_push_notifications:IndicoPushNotificationsPlugin"
        ]
    },
    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Plugins",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    # Keywords
    keywords="indico plugin push notifications telegram webpush",
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/indico/indico-plugins/issues",
        "Source": "https://github.com/indico/indico-plugins/tree/master/indico-push-notifications",
        "Documentation": "https://docs.getindico.io/en/stable/plugins/push-notifications/",
    },
)
