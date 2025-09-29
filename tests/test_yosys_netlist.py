# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys component"""

import json
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent, YosysComponentException
from digsim.utils import YosysNetlist


netlist_dict_if_one = {
    "modules": {
        "counter": {
            "ports": {
                "in_port": {"direction": "input", "bits": [2, 3, 4, 5]},
                "out_port": {"direction": "output", "bits": [5, 4, 3, 2]},
            },
            "cells": {},
        }
    }
}

netlist_dict_if_two = {
    "modules": {
        "counter": {
            "ports": {
                "in_port": {"direction": "input", "bits": [2, 3, 4, 5]},
                "out_port": {"direction": "output", "bits": [2, 3, 4, 5]},
            },
            "cells": {},
        }
    }
}

netlist_dict_if_three = {
    "modules": {
        "counter": {
            "ports": {
                "in_port": {"direction": "input", "bits": [2, 3, 4, 5, 6]},
                "out_port": {"direction": "output", "bits": [2, 3, 4, 5]},
            },
            "cells": {},
        }
    }
}

netlist_dict_if_four = {
    "modules": {
        "counter": {
            "ports": {
                "in_port": {"direction": "input", "bits": [2, 3, 4, 5]},
                "out_port": {"direction": "output", "bits": [2, 3, 4, 5, 2]},
            },
            "cells": {},
        }
    }
}

netlist_dict_if_2outports = {
    "modules": {
        "counter": {
            "ports": {
                "in_port": {"direction": "input", "bits": [2, 3, 4, 5]},
                "out_port_a": {"direction": "output", "bits": [2, 3, 4, 5]},
                "out_port_b": {"direction": "output", "bits": [2, 3, 4, 5]},
            },
            "cells": {},
        }
    }
}

netlist_dict_if_3outports = {
    "modules": {
        "counter": {
            "ports": {
                "in_port": {"direction": "input", "bits": [2, 3, 4, 5]},
                "out_port_a": {"direction": "output", "bits": [2, 3, 4, 5]},
                "out_port_b": {"direction": "output", "bits": [2, 3, 4, 5]},
                "out_port_c": {"direction": "output", "bits": [2, 3, 4, 5]},
            },
            "cells": {},
        }
    }
}


def test_yosys_component_create():
    """Test create YosysComponent"""
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict_if_one)
    comp.create_from_netlist(yosys_netlist)

    comp.in_port.value = 0xA
    circuit.run(ms=1)
    assert comp.out_port.value == 0x5


def test_yosys_component_create_reload():
    """Test create YosysComponent - and reload changed netlist OK"""
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict_if_one)
    comp.create_from_netlist(yosys_netlist)

    comp.in_port.value = 0xA
    circuit.run(ms=1)
    assert comp.out_port.value == 0x5

    yosys_netlist = YosysNetlist(**netlist_dict_if_two)
    comp.reload_from_netlist(yosys_netlist)

    comp.in_port.value = 0xA
    circuit.run(ms=1)
    assert comp.out_port.value == 0xA


def test_yosys_component_create_reload_fail_portwidth():
    """Test create YosysComponent - and reload changed netlist OK"""
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict_if_one)
    comp.create_from_netlist(yosys_netlist)

    yosys_netlist = YosysNetlist(**netlist_dict_if_three)

    # Fail due to wider in_port
    with pytest.raises(YosysComponentException):
        comp.reload_from_netlist(yosys_netlist)

    yosys_netlist = YosysNetlist(**netlist_dict_if_four)

    # Fail due to wider out_port
    with pytest.raises(YosysComponentException):
        comp.reload_from_netlist(yosys_netlist)


def test_yosys_component_create_reload_fail_extra_ports():
    """Test create YosysComponent - and reload changed netlist OK"""
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict_if_2outports)
    comp.create_from_netlist(yosys_netlist)

    yosys_netlist = YosysNetlist(**netlist_dict_if_3outports)

    # Fail due to extra port
    with pytest.raises(YosysComponentException):
        comp.reload_from_netlist(yosys_netlist)


def test_yosys_component_create_reload_fail_less_ports():
    """Test create YosysComponent - and reload changed netlist OK"""
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict_if_3outports)
    comp.create_from_netlist(yosys_netlist)

    yosys_netlist = YosysNetlist(**netlist_dict_if_2outports)

    # Fail due to extra port
    with pytest.raises(YosysComponentException):
        comp.reload_from_netlist(yosys_netlist)


def test_yosys_component_create_static_levels():
    """Test create YosysComponent - with static levels"""
    netlist_dict_static = {
        "modules": {
            "counter": {
                "ports": {
                    "out_port": {
                        "direction": "output",
                        "bits": ["0", "1", "0", "1", "0", "0", "1", "1"],
                    },
                },
                "cells": {},
            }
        }
    }
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict_static)
    comp.create_from_netlist(yosys_netlist)
    circuit.init()
    circuit.run(ms=1)
    assert comp.out_port.value == 0xCA


def test_yosys_component_not_gate_multiple_outputs():
    """Test create YosysComponent - with static levels"""
    netlist_dict = {
        "modules": {
            "counter": {
                "ports": {
                    "in_port": {
                        "direction": "input",
                        "bits": [2],
                    },
                    "out_port": {
                        "direction": "output",
                        "bits": [3, 3, 3, 3],
                    },
                },
                "cells": {
                    "not_gate": {
                        "type": "$_NOT_",
                        "port_directions": {"A": "input", "Y": "output"},
                        "connections": {"A": [2], "Y": [3]},
                    }
                },
            }
        }
    }
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict)
    comp.create_from_netlist(yosys_netlist)
    circuit.init()
    comp.in_port.value = 0
    circuit.run(ms=1)
    assert comp.out_port.value == 0xF
    comp.in_port.value = 1
    circuit.run(ms=1)
    assert comp.out_port.value == 0x0


def test_yosys_component_not_gate_static_input():
    """Test create YosysComponent - with static levels"""
    netlist_dict = {
        "modules": {
            "counter": {
                "ports": {
                    "out_port": {
                        "direction": "output",
                        "bits": [2],
                    },
                },
                "cells": {
                    "not_gate": {
                        "type": "$_NOT_",
                        "port_directions": {"A": "input", "Y": "output"},
                        "connections": {"A": ["0"], "Y": [2]},
                    }
                },
            }
        }
    }
    circuit = Circuit()
    comp = YosysComponent(circuit)
    yosys_netlist = YosysNetlist(**netlist_dict)
    comp.create_from_netlist(yosys_netlist)
    circuit.init()
    assert comp.out_port.value == "X"
    circuit.run(ms=1)
    assert comp.out_port.value == 1


def test_yosys_complex_netlist():
    comlex_json_netlist_file = (
        Path(__file__).parent.parent / "src/digsim/circuit/components/ic/74162.json"
    )
    with open(comlex_json_netlist_file, encoding="utf-8") as json_file:
        netlist_dict = json.load(json_file)
    YosysNetlist(**netlist_dict)
