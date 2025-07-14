#!/usr/bin/env python
"""Setup script for ajenitk-context."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="ajenitk-context",
    version="0.1.0",
    author="Ajenitk Team",
    author_email="team@ajenitk.com",
    description="Ajentik AI system with PydanticAI, Logfire, and CLI interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ajenitk-context",
    packages=find_packages(include=["src", "src.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pydantic-ai[logfire]>=0.1.0",
        "pydantic>=2.0",
        "click>=8.0",
        "rich>=13.0",
        "questionary>=2.0",
        "python-dotenv>=1.0",
        "httpx>=0.25",
        "typing-extensions>=4.8",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
            "pytest-mock>=3.0",
            "black>=23.0",
            "ruff>=0.1",
            "mypy>=1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "ajentik=src.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json", "*.yaml", "*.yml"],
    },
    zip_safe=False,
)