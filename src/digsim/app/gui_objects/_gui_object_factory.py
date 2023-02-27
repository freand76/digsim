# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A GUI component object factory module """

from ._bus_bit_object import BitsBusObject, BusBitsObject
from ._gui_note_object import GuiNoteObject
from ._hexdigit_object import HexDigitObject
from ._image_objects import (
    ImageObjectAND,
    ImageObjectClock,
    ImageObjectDFF,
    ImageObjectIC,
    ImageObjectLed,
    ImageObjectMUX,
    ImageObjectNAND,
    ImageObjectNOR,
    ImageObjectNOT,
    ImageObjectOnOffSwitch,
    ImageObjectOR,
    ImageObjectPushButton,
    ImageObjectStaticValue,
    ImageObjectXOR,
    ImageObjectYosys,
)
from ._seven_segment_object import SevenSegmentObject


class ComponentObjectFactoryError(Exception):
    """ComponentObjectFactoryError"""


CLASS_NAME_TO_COMPONENT_OBJECT = {
    "AND": ImageObjectAND,
    "Bus2Bits": BusBitsObject,
    "Bits2Bus": BitsBusObject,
    "Clock": ImageObjectClock,
    "DFF": ImageObjectDFF,
    "HexDigit": HexDigitObject,
    "Led": ImageObjectLed,
    "NAND": ImageObjectNAND,
    "NOR": ImageObjectNOR,
    "NOT": ImageObjectNOT,
    "MUX": ImageObjectMUX,
    "OR": ImageObjectOR,
    "OnOffSwitch": ImageObjectOnOffSwitch,
    "PushButton": ImageObjectPushButton,
    "SevenSegment": SevenSegmentObject,
    "StaticValue": ImageObjectStaticValue,
    "XOR": ImageObjectXOR,
    "IntegratedCircuit": ImageObjectIC,
    "YosysComponent": ImageObjectYosys,
    "Note": GuiNoteObject,
}


def get_class_by_name(component_class_name):
    """A function that returns the GUI for a component class (str or class)"""

    if component_class_name in CLASS_NAME_TO_COMPONENT_OBJECT:
        return CLASS_NAME_TO_COMPONENT_OBJECT[component_class_name]

    # Raise exception if component not found
    raise ComponentObjectFactoryError(f"Unknown component '{component_class_name}'")
