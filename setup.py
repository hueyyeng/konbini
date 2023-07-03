from pathlib import Path

from setuptools import find_packages, setup

from konbini import __version__ as version

PROJECT_NAME = "konbini"
PROJECT_ROOT = Path(__file__).parent
EXCLUDE_FOLDERS = [
    "docs",
    "examples",
    "tests",
]

with open(str(PROJECT_ROOT / "README.md"), "r", encoding="utf-8") as readme:
    README = readme.read()

with open(str(PROJECT_ROOT / "requirements.txt"), "r") as req:
    _ = req.read()
    REQUIREMENTS = _.strip().split("\n")

setup(
    name=PROJECT_NAME,
    version=version,
    url="https://github.com/hueyyeng/konbini",
    author="Huey Yeng",
    author_email="huey.yeng.mmu@gmail.com",
    maintainer="Huey Yeng",
    maintainer_email="huey.yeng.mmu@gmail.com",
    description="Opinionated Autodesk Shotgun/ShotGrid API Wrapper.",
    long_description_content_type="text/markdown",
    long_description=README,
    packages=find_packages(where=str(PROJECT_ROOT), exclude=EXCLUDE_FOLDERS),
    include_package_data=True,
    install_requires=REQUIREMENTS,
    python_requires=">=3.7",
    keywords=[
        "python",
        "library",
        "shotgrid",
        "shotgun",
        "api",
        "autodesk"
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.7",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows :: Windows 10",
    ]
)
