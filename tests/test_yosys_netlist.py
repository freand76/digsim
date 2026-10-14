# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Pystest module to test functionality of yosys component"""

import json
from pathlib import Path

import pytest

from digsim.circuit import Circuit
from digsim.circuit.components import YosysComponent, YosysComponentException
from digsim.utils import YosysNetlist
from digsim.utils._yosys_netlist import YosysModule, YosysPort


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


def _module(**ports):
    return YosysModule(
        ports={
            name: YosysPort(direction=direction, bits=list(range(width)))
            for name, (direction, width) in ports.items()
        }
    )


def test_yosys_module_same_interface():
    """Modules have the same interface with the same port names, directions and widths"""
    module = _module(a=("input", 2), y=("output", 1))
    assert module.is_same_interface(_module(y=("output", 1), a=("input", 2)))
    assert not module.is_same_interface(_module(a=("input", 2)))
    assert not module.is_same_interface(_module(a=("input", 2), z=("output", 1)))
    assert not module.is_same_interface(_module(a=("input", 3), y=("output", 1)))
    assert not module.is_same_interface(_module(a=("output", 2), y=("output", 1)))


@pytest.mark.parametrize("content", ["{", '{"modules": 3}'])
def test_yosys_component_malformed_netlist(tmp_path, content):
    """A file that is not a Yosys netlist gives a component exception"""
    netlist_file = tmp_path / "netlist.json"
    netlist_file.write_text(content)
    with pytest.raises(YosysComponentException):
        YosysComponent(Circuit(), path=netlist_file)


def test_yosys_component_from_netlist_has_no_file():
    """A component created from a netlist object can't be saved or reloaded from a file"""
    netlist_file = Path(__file__).parent.parent / "examples" / "yosys_counter" / "counter.json"
    netlist = YosysNetlist(**json.loads(netlist_file.read_text()))
    circuit = Circuit(name="counter")
    counter = YosysComponent(circuit)
    counter.create_from_netlist(netlist)
    with pytest.raises(YosysComponentException, match="no file"):
        circuit.to_dataclass()
    with pytest.raises(YosysComponentException, match="no file"):
        counter.reload_file()


def test_yosys_component_wiring():
    """Inputs wired to outputs and to several cells, and constants on outputs"""
    netlist_dict = {
        "modules": {
            "wiring": {
                "ports": {
                    "a": {"direction": "input", "bits": [2]},
                    # A copy of 'a', a constant 1 and 0, and 'a' through two NOT gates
                    "y": {"direction": "output", "bits": [2, "1", "0", 3, 4]},
                },
                "cells": {
                    "not_1": {
                        "type": "$_NOT_",
                        "port_directions": {"A": "input", "Y": "output"},
                        "connections": {"A": [2], "Y": [3]},
                    },
                    "not_2": {
                        "type": "$_NOT_",
                        "port_directions": {"A": "input", "Y": "output"},
                        "connections": {"A": [2], "Y": [4]},
                    },
                },
            }
        }
    }
    circuit = Circuit()
    comp = YosysComponent(circuit)
    comp.create_from_netlist(YosysNetlist(**netlist_dict))
    circuit.init()
    # Bit 0 of 'y' is the first bit in the netlist
    for a, expected in [(0, 0b11010), (1, 0b00011)]:
        comp.a.value = a
        circuit.run(ms=1)
        assert comp.y.value == expected


def test_yosys_component_unused_input():
    """An input that the design does not use (like 'b' in 'assign y = a') is allowed"""
    netlist_dict = {
        "modules": {
            "unused_input": {
                "ports": {
                    "a": {"direction": "input", "bits": [2]},
                    "b": {"direction": "input", "bits": [3]},
                    "y": {"direction": "output", "bits": [2]},
                },
                "cells": {},
            }
        }
    }
    circuit = Circuit()
    comp = YosysComponent(circuit)
    comp.create_from_netlist(YosysNetlist(**netlist_dict))
    circuit.init()
    comp.a.value = 1
    circuit.run(ms=1)
    assert comp.y.value == 1


def test_yosys_component_unused_cell_output():
    """A cell output that drives nothing is allowed"""
    netlist_dict = {
        "modules": {
            "unused_output": {
                "ports": {
                    "a": {"direction": "input", "bits": [2]},
                    "y": {"direction": "output", "bits": [2]},
                },
                "cells": {
                    "not_gate": {
                        "type": "$_NOT_",
                        "port_directions": {"A": "input", "Y": "output"},
                        "connections": {"A": [2], "Y": [5]},
                    }
                },
            }
        }
    }
    circuit = Circuit()
    comp = YosysComponent(circuit)
    comp.create_from_netlist(YosysNetlist(**netlist_dict))
    circuit.init()
    comp.a.value = 1
    circuit.run(ms=1)
    assert comp.y.value == 1
