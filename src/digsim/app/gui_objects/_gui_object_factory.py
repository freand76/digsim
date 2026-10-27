# Copyright (c) Fredrik Andersson, 2023-2026
# All rights reserved

"""A GUI component object factory module"""

from digsim.circuit.components.atoms import DigsimException

from ._buzzer_object import BuzzerObject
from ._component_object import ComponentObject
from ._device_objects import (
    ButtonObject,
    ClockObject,
    FlipFlopObject,
    OnOffSwitchObject,
    StaticValueObject,
)
from ._dip_switch_object import DipSwitchObject
from ._gui_note_object import GuiNoteObject
from ._hexdigit_object import HexDigitObject
from ._label_object import LabelWireInObject, LabelWireOutObject
from ._led_bar_object import LedBarObject
from ._logic_analyzer_object import LogicAnalyzerObject
from ._named_box_object import (
    AdderObject,
    ComparatorObject,
    ICObject,
    MultiplierObject,
    NegatorObject,
    RAMObject,
    ROMObject,
    SubtractorObject,
)
from ._probe_object import ProbeObject
from ._seven_segment_object import SevenSegmentObject
from ._symbol_objects import (
    AndObject,
    BitsBusObject,
    BusBitsObject,
    LedObject,
    MuxObject,
    NandObject,
    NorObject,
    NotObject,
    OrObject,
    TristateObject,
    XnorObject,
    XorObject,
)
from ._yosys_object import YosysObject


class ComponentObjectFactoryError(DigsimException):
    """ComponentObjectFactoryError"""


CLASS_NAME_TO_COMPONENT_OBJECT: dict[str, type[ComponentObject]] = {
    "AND": AndObject,
    "Adder": AdderObject,
    "Comparator": ComparatorObject,
    "Multiplier": MultiplierObject,
    "Negator": NegatorObject,
    "Subtractor": SubtractorObject,
    "Bus2Wires": BusBitsObject,
    "Wires2Bus": BitsBusObject,
    "Clock": ClockObject,
    "DipSwitch": DipSwitchObject,
    "DFF": FlipFlopObject,
    "HexDigit": HexDigitObject,
    "LabelWireIn": LabelWireInObject,
    "LabelWireOut": LabelWireOutObject,
    "Led": LedObject,
    "LogicAnalyzer": LogicAnalyzerObject,
    "NAND": NandObject,
    "NOR": NorObject,
    "NOT": NotObject,
    "MUX": MuxObject,
    "OR": OrObject,
    "OnOffSwitch": OnOffSwitchObject,
    "Probe": ProbeObject,
    "PushButton": ButtonObject,
    "SevenSegment": SevenSegmentObject,
    "StaticValue": StaticValueObject,
    "XOR": XorObject,
    "XNOR": XnorObject,
    "LedBar": LedBarObject,
    "IntegratedCircuit": ICObject,
    "RAM": RAMObject,
    "ROM": ROMObject,
    "YosysComponent": YosysObject,
    "Note": GuiNoteObject,
    "FlipFlop": FlipFlopObject,
    "SRFF": FlipFlopObject,
    "ClockedSRFF": FlipFlopObject,
    "ClockedJKFF": FlipFlopObject,
    "ClockedTFF": FlipFlopObject,
    "Buzzer": BuzzerObject,
    "TristateBuffer": TristateObject,
}


def class_factory(component_class_name: str) -> type[ComponentObject]:
    """A function that returns the GUI for a component class (str or class)"""

    if component_class_name in CLASS_NAME_TO_COMPONENT_OBJECT:
        return CLASS_NAME_TO_COMPONENT_OBJECT[component_class_name]

    # Raise exception if component not found
    raise ComponentObjectFactoryError(f"Unknown component '{component_class_name}'")
