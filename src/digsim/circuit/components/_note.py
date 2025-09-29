# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Components that only exist in the model"""

from .atoms import Component


class Note(Component):
    """Note component"""

    def __init__(self, circuit, name=None, text=""):
        super().__init__(circuit, name)
        self.parameter_set("text", text)

    @classmethod
    def get_parameters(cls):
        return {
            "text": {
                "type": "str",
                "default": "Write something here...",
                "description": "Note text",
                "reconfigurable": True,
            },
        }
