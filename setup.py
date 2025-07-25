"""
Setup configuration for Weather Map Application.
"""

from setuptools import setup, find_packages  # type: ignore

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="weather-map-app",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Streamlit application for displaying weather information and interactive maps for cities worldwide",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/weather-map-app",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "weather-map=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
