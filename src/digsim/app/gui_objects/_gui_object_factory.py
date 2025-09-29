# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""A GUI component object factory module"""

from digsim.circuit.components.atoms import DigsimException

from ._bus_bit_object import BitsBusObject, BusBitsObject
from ._buzzer_object import BuzzerObject
from ._dip_switch_object import DipSwitchObject
from ._gui_note_object import GuiNoteObject
from ._hexdigit_object import HexDigitObject
from ._image_objects import (
    ImageObjectAND,
    ImageObjectClock,
    ImageObjectDFF,
    ImageObjectFlipFlop,
    ImageObjectIC,
    ImageObjectLed,
    ImageObjectMUX,
    ImageObjectNAND,
    ImageObjectNOR,
    ImageObjectNOT,
    ImageObjectOR,
    ImageObjectStaticValue,
    ImageObjectXOR,
)
from ._label_object import LabelObject
from ._logic_analyzer_object import LogicAnalyzerObject
from ._seven_segment_object import SevenSegmentObject
from ._shortcut_objects import ButtonObject, OnOffSwitchObject
from ._yosys_object import YosysObject


class ComponentObjectFactoryError(DigsimException):
    """ComponentObjectFactoryError"""


CLASS_NAME_TO_COMPONENT_OBJECT = {
    "AND": ImageObjectAND,
    "Bus2Wires": BusBitsObject,
    "Wires2Bus": BitsBusObject,
    "Clock": ImageObjectClock,
    "DipSwitch": DipSwitchObject,
    "DFF": ImageObjectDFF,
    "HexDigit": HexDigitObject,
    "LabelWireIn": LabelObject,
    "LabelWireOut": LabelObject,
    "Led": ImageObjectLed,
    "LogicAnalyzer": LogicAnalyzerObject,
    "NAND": ImageObjectNAND,
    "NOR": ImageObjectNOR,
    "NOT": ImageObjectNOT,
    "MUX": ImageObjectMUX,
    "OR": ImageObjectOR,
    "OnOffSwitch": OnOffSwitchObject,
    "PushButton": ButtonObject,
    "SevenSegment": SevenSegmentObject,
    "StaticValue": ImageObjectStaticValue,
    "XOR": ImageObjectXOR,
    "IntegratedCircuit": ImageObjectIC,
    "YosysComponent": YosysObject,
    "Note": GuiNoteObject,
    "FlipFlop": ImageObjectFlipFlop,
    "SRFF": ImageObjectFlipFlop,
    "ClockedSRFF": ImageObjectFlipFlop,
    "ClockedJKFF": ImageObjectFlipFlop,
    "ClockedTFF": ImageObjectFlipFlop,
    "Buzzer": BuzzerObject,
}


def class_factory(component_class_name):
    """A function that returns the GUI for a component class (str or class)"""

    if component_class_name in CLASS_NAME_TO_COMPONENT_OBJECT:
        return CLASS_NAME_TO_COMPONENT_OBJECT[component_class_name]

    # Raise exception if component not found
    raise ComponentObjectFactoryError(f"Unknown component '{component_class_name}'")
