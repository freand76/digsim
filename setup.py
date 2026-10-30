# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""
The packages, the ones in src/ and the example circuits: circuits/ is the package
digsim.examples, for File > Examples (the rest of the project is in pyproject.toml)
"""

from setuptools import find_namespace_packages, setup


setup(
    packages=[*find_namespace_packages("src"), "digsim.examples"],
    package_dir={"": "src", "digsim.examples": "circuits"},
    package_data={"digsim.examples": ["**/*"]},
    # The build outputs that .gitignore leaves out, like those of rv32e/rv32e_code
    exclude_package_data={
        "digsim.examples": ["**/*.elf", "**/*.lst", "**/*.hex", "**/*.o", "**/*.map"]
    },
)
