# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""
Module for creating a yosys component in the ic folder
"""

from pathlib import Path

from ._yosys_component import YosysComponent


class IntegratedCircuit(YosysComponent):
    """IC component class (predefined yosys module)"""

    def __init__(self, circuit, name="IC", ic_name=None):
        path = f"{self.folder()}/{ic_name}.json"
        super().__init__(circuit, name=name, path=path)
        self.parameter_set("ic_name", ic_name)

    @classmethod
    def folder(cls):
        """Get predefined IC folder"""
        return str(Path(__file__).parent / "ic")

    def settings_to_dict(self):
        return {"ic_name": self.parameter_get("ic_name")}

    @classmethod
    def get_parameters(cls):
        return {
            "ic_name": {
                "type": "ic_name",
                "description": "Select IC",
            }
        }
