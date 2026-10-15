# Yosys Netlist

The classes in `digsim.utils` read a Yosys JSON netlist, for example to build a
[YosysComponent](components.md#digsim.circuit.components.YosysComponent) from it:

```python
from digsim.utils import YosysNetlist

netlist = YosysNetlist(**synthesis.synth_to_dict())
counter.create_from_netlist(netlist)
```

::: digsim.utils.YosysNetlist
    options:
      members:
        - modules
        - get_modules

::: digsim.utils.YosysModule
    options:
      members:
        - ports
        - cells
        - is_same_interface

::: digsim.utils.YosysPort
    options:
      members:
        - direction
        - bits
        - is_output

::: digsim.utils.YosysCell
    options:
      members:
        - type
        - port_directions
        - connections
