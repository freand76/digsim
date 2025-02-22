# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

"""
Module with classes to parse a yosys netlist
"""


class _NetlistPort:
    """A class describing a port within a netlist"""

    def __init__(self, parent, name, net=None, is_source=None):
        self._parent = parent
        self._name = name
        self._is_source = is_source
        self._sinks = []
        if net is None:
            self._nets = []
        else:
            self._nets = [net]

    def name(self):
        """Return port name"""
        return self._name

    def get_parent(self):
        """Return port parent"""
        return self._parent

    def is_source(self):
        """Return true if port is a source (false for sink)"""
        return self._is_source

    def add_sinks(self, sinks):
        """Add sinks to source port"""
        self._sinks.extend(sinks)

    def get_sinks(self):
        """Get source port sinks"""
        return self._sinks

    def get_nets(self):
        """Get port nets"""
        return self._nets

    def from_module_dict(self, port_dict, global_nets):
        """Create xternal port from module dict"""
        self._is_source = port_dict["direction"] == "input"
        for net in port_dict["bits"]:
            if net not in global_nets:
                global_nets.append(net)
            self._nets.append(net)


class _NetlistBlock:
    """Common base class for modules and cells"""

    def __init__(self, name, block_type=None):
        self._name = name
        self._ports = {}
        self._nets = []
        self._block_type = block_type
        self._net_to_source_port = {}
        self._net_to_sink_ports = {}

    def name(self):
        """Return name of block (cell or module)"""
        return self._name

    def get_type(self):
        """Get type"""
        return self._block_type

    def set_type(self, block_type):
        """Set type"""
        self._block_type = block_type

    def add_port(self, name, port):
        """Add port to block (cell or module)"""
        self._ports[name] = port
        nets = port.get_nets()
        if port.is_source():
            for net in nets:
                self._net_to_source_port[net] = port
        else:
            for net in nets:
                if net not in self._net_to_sink_ports:
                    self._net_to_sink_ports[net] = []
                if port not in self._net_to_sink_ports[net]:
                    self._net_to_sink_ports[net].append(port)

    def get_nets(self):
        """Get nets of block (cell or module)"""
        return self._nets

    def get_source_ports(self):
        """Get source ports of block (cell or module)"""
        ports = []
        for _, port in self._net_to_source_port.items():
            ports.append(port)
        return ports

    def get_source_port(self, net):
        """Get source port of block (cell or module)"""
        return self._net_to_source_port.get(net)

    def get_sink_ports(self, net):
        """Get sink port of block (cell or module)"""
        return self._net_to_sink_ports.get(net, [])


class _NetlistCell(_NetlistBlock):
    """A class holding a cell in a yosys netlist"""

    def __init__(self, name):
        super().__init__(name)

    def get_friendly_name(self):
        """Return a friendly name for a netlist cell"""
        return f"{self.name().split('$')[-1]}_{self.get_friendly_type()}"

    def get_friendly_type(self):
        """Return a friendly type for a netlist cell"""
        return f"_{self.get_type()[2:-1]}_"

    def from_dict(self, cell_dict, global_nets):
        """Create netlist cell from dict"""
        self.set_type(cell_dict["type"])
        for port_name, port_dir in cell_dict["port_directions"].items():
            output = port_dir == "output"
            port_net = cell_dict["connections"][port_name]
            self._nets.extend(port_net)
            for net in port_net:
                if net not in global_nets:
                    global_nets.append(net)
                port = _NetlistPort(self, port_name, net, output)
                self.add_port(port_name, port)


class _NestlistModule(_NetlistBlock):
    """A class holding a module in a yosys netlist"""

    def __init__(self, name):
        super().__init__(name, "module")
        self._cells = {}
        self._module_nets = []
        self._ext_if = {}

        static_cell = _NetlistCell("StaticLevel")
        static_cell.from_dict(
            {
                "type": "$_StaticLevel_",
                "port_directions": {"L": "output", "H": "output"},
                "connections": {"L": ["0"], "H": ["1"]},
            },
            self._nets,
        )
        self._cells["StaticLevel"] = static_cell

    def from_dict(self, module_dict):
        """Create module from dict"""
        for ext_port_name, port_dict in module_dict["ports"].items():
            ext_port = _NetlistPort(self, ext_port_name)
            ext_port.from_module_dict(port_dict, self._nets)
            nets = ext_port.get_nets()
            ext_port_dict = {"output": ext_port.is_source(), "nets": nets}
            self._ext_if[ext_port_name] = ext_port_dict
            self.add_port(ext_port_name, ext_port)

        for cell_name, cell_dict in module_dict["cells"].items():
            cell = _NetlistCell(cell_name)
            cell.from_dict(cell_dict, self._nets)
            self._cells[cell_name] = cell

    def get_cells(self):
        """Get cells dict"""
        return self._cells

    def get_external_interface(self):
        """Get external interface dict"""
        return self._ext_if

    def get_source(self, net):
        """Get source port for net"""
        module_port = self.get_source_port(net)
        if module_port is not None:
            return module_port
        for _, cell in self._cells.items():
            cell_port = cell.get_source_port(net)
            if cell_port is not None:
                return cell_port
        return None

    def get_sinks(self, net):
        """Get module sinks (input ports)"""
        sink_ports = self.get_sink_ports(net)
        for _, cell in self._cells.items():
            cell_sink_ports = cell.get_sink_ports(net)
            for port in cell_sink_ports:
                if port not in sink_ports:
                    sink_ports.append(port)
        return sink_ports

    def connect(self):
        """Connect all nets within module"""
        _source_port_dict = {}
        _sink_ports_dict = {}
        _cells_dict = {}

        # Build net to cell dict
        for _, cell in self._cells.items():
            for cell_net in cell.get_nets():
                if cell_net not in _cells_dict:
                    _cells_dict[cell_net] = []
                _cells_dict[cell_net].append(cell)

        # Build net to ports dict
        for net in self._nets:
            # Module
            port = self.get_source_port(net)
            if port is not None:
                _source_port_dict[net] = port
            sink_ports = self.get_sink_ports(net)
            # Cells
            for cell in _cells_dict.get(net, []):
                port = cell.get_source_port(net)
                if port is not None:
                    _source_port_dict[net] = port
                cell_sink_ports = cell.get_sink_ports(net)
                sink_ports.extend(cell_sink_ports)
            _sink_ports_dict[net] = sink_ports

        # Connect
        for net in self._nets:
            source_port = _source_port_dict[net]
            sink_ports = _sink_ports_dict[net]
            source_port.add_sinks(sink_ports)

        # Connect module nets
        for module_net in self._module_nets:
            nets = module_net.get_nets()
            ports = []
            for net in nets:
                port = _source_port_dict[net]
                ports.append(port)
            module_net.set_ports(ports)

    def get_module_nets(self):
        """Get the nets for this module"""
        return self._module_nets


class YosysNetlist:
    """A class holding the content of a yosys netlist"""

    def __init__(self):
        self._modules = {}

    def get_modules(self):
        """Get modules dict"""
        return self._modules

    def from_dict(self, netlist_dict):
        """Parse netlist from dict"""
        for module_name, module_dict in netlist_dict["modules"].items():
            module = _NestlistModule(module_name)
            module.from_dict(module_dict)
            self._modules[module_name] = module
        for _, module in self._modules.items():
            module.connect()
