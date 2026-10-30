# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The packages, the ones in src/ and the example circuits: circuits/ is the package
digsim.examples, for File > Examples (the rest of the project is in pyproject.toml)
"""

from setuptools import find_namespace_packages, setup


# The example folders are packages too, of data: setuptools warns about folders under a
# package that aren't in the packages
EXAMPLES = [
    "digsim.examples",
    *(f"digsim.examples.{name}" for name in find_namespace_packages("circuits")),
]

setup(
    packages=[*find_namespace_packages("src"), *EXAMPLES],
    package_dir={"": "src", "digsim.examples": "circuits"},
    package_data={name: ["*"] for name in EXAMPLES},
    # The build outputs that .gitignore leaves out, like those of rv32e/rv32e_code
    exclude_package_data={name: ["*.elf", "*.lst", "*.hex"] for name in EXAMPLES},
)
