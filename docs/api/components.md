# Components

All components are in `digsim.circuit.components`. They are created with the circuit
as their first argument, and an optional name:

```python
from digsim.circuit import Circuit
from digsim.circuit.components import AND

circuit = Circuit()
gate = AND(circuit, "gate", ports=3)
```

The base class of all components, with the methods they share, is
[Component](base-classes.md#digsim.circuit.components.atoms.Component).

## Inputs

::: digsim.circuit.components.PushButton
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.OnOffSwitch
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.DipSwitch
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Clock
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.StaticValue
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.VDD
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.GND
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Outputs

::: digsim.circuit.components.Led
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.LedBar
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.HexDigit
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.SevenSegment
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Buzzer
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.LogicAnalyzer
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Probe
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Gates

::: digsim.circuit.components.AND
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.OR
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.NOT
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.XOR
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.XNOR
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.NAND
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.NOR
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.MUX
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Decoder
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Demultiplexer
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Flip-flops

::: digsim.circuit.components.DFF
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.SR
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.SRFF
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.ClockedSRFF
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.ClockedJKFF
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.ClockedTFF
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.FlipFlop
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Counter
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Arithmetic

::: digsim.circuit.components.Adder
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Subtractor
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Multiplier
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Comparator
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Negator
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Buses and labels

::: digsim.circuit.components.Bus2Wires
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.Wires2Bus
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.TristateBuffer
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.LabelWireIn
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.LabelWireOut
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Circuit ports

::: digsim.circuit.components.CircuitInput
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.CircuitOutput
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.CircuitInOut
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.SubCircuit
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Verilog and ICs

::: digsim.circuit.components.YosysComponent
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.IntegratedCircuit
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Memory

::: digsim.circuit.components.RAM
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.ROM
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

::: digsim.circuit.components.MemStdOut
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]

## Other

::: digsim.circuit.components.Note
    options:
      heading_level: 3
      filters: ["!^_", "!^update$", "!^default_state$", "!^get_parameters$", "!^get_circuit_parameters$", "!^reconfigure$", "!^init$", "!^has_action$", "!^onpress$", "!^onrelease$", "!^settings_to_dict$", "!^clear$", "!^remove_connections$", "!^active$", "!^PORTLIST$", "!^VAL_TO_SEGMENTS$", "!^TONE_TO_FREQUENCY$", "!^folder$", "!^segments$", "!^select$", "!^selected$", "!^signal_data$", "!^data_dict$", "!^port_in$", "!^port_out$"]
