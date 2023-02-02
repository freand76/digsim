# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

""" A GUI component object factory module """

from ._placed_component import PlacedComponent
from ._placed_hexdigit import PlacedHexDigit
from ._placed_image_component import (
    PlacedImageComponentAND,
    PlacedImageComponentClock,
    PlacedImageComponentDFF,
    PlacedImageComponentLed,
    PlacedImageComponentNAND,
    PlacedImageComponentNOR,
    PlacedImageComponentNOT,
    PlacedImageComponentOnOffSwitch,
    PlacedImageComponentOR,
    PlacedImageComponentPushButton,
    PlacedImageComponentXOR,
)
from ._placed_seven_segment import PlacedSevenSegment
from ._placed_yosys import PlacedYosys


CLASS_NAME_TO_PLACED_COMPONENT = {
    "Clock": PlacedImageComponentClock,
    "DFF": PlacedImageComponentDFF,
    "HexDigit": PlacedHexDigit,
    "Led": PlacedImageComponentLed,
    "NAND": PlacedImageComponentNAND,
    "NOR": PlacedImageComponentNOR,
    "NOT": PlacedImageComponentNOT,
    "OR": PlacedImageComponentOR,
    "OnOffSwitch": PlacedImageComponentOnOffSwitch,
    "PushButton": PlacedImageComponentPushButton,
    "SevenSegment": PlacedSevenSegment,
    "XOR": PlacedImageComponentXOR,
    "Yosys": PlacedYosys,
    "AND": PlacedImageComponentAND,
}


def get_placed_component_by_name(component_class_name):
    """A function that returns the GUI for a component class (str or class)"""

    if component_class_name in CLASS_NAME_TO_PLACED_COMPONENT:
        return CLASS_NAME_TO_PLACED_COMPONENT[component_class_name]

    # Default placed component
    return PlacedComponent
