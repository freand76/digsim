# Component Base Classes

The classes in `digsim.circuit.components.atoms` that all components are built on. Every
component has the methods of `Component`, like `name()`, `port()` and `inports()`.
Subclass them to write [your own components](../components.md).

::: digsim.circuit.components.atoms.Component
    options:
      members:
        - name
        - set_name
        - display_name
        - set_display_name
        - circuit
        - ports
        - port
        - inports
        - outports
        - path
        - parent
        - is_toplevel
        - wire
        - active
        - add_port
        - parameter_set
        - parameter_get
        - update
        - default_state
        - init
        - get_parameters
        - reconfigure
        - settings_to_dict
        - has_action
        - onpress
        - onrelease

::: digsim.circuit.components.atoms.CallbackComponent
    options:
      members:
        - set_callback

::: digsim.circuit.components.atoms.MultiComponent
    options:
      members:
        - add

## Exceptions

::: digsim.circuit.components.atoms.DigsimException
    options:
      heading_level: 3
      members: false

::: digsim.circuit.components.atoms.ComponentException
    options:
      heading_level: 3
      members: false
