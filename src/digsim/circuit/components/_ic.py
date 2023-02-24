# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Module for creating a yosys component in the ic folder
"""
import os

from ._yosys_component import YosysComponent


class IntegratedCircuit(YosysComponent):
    """IC component class (predefined yosys module)"""

    def __init__(self, circuit, name="IC", ic_name=None):
        self._ic_name = ic_name
        path = f"{self.folder()}/{ic_name}.json"
        super().__init__(circuit, name=name, path=path)

    @classmethod
    def folder(cls):
        """Get predefined IC folder"""
        return f"{os.path.dirname(__file__)}/ic"

    def settings_to_dict(self):
        return {"ic_name": self._ic_name}

    @classmethod
    def get_parameters(cls):
        return {
            "ic_name": {
                "type": "ic_name",
                "description": "Select IC",
            }
        }
