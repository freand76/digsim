import abc
import importlib


class Component(abc.ABC):
    def __init__(self, circuit, name=""):
        self._circuit = circuit
        self._name = name
        self._parent = None
        self._ports = []
        self._circuit.add_component(self)

    def init(self):
        pass

    def add_port(self, port):
        self.__dict__[port.name] = port
        self._ports.append(port)

    @property
    def path(self):
        if self._parent is not None:
            return f"{self._parent.path}.{self.name}"
        return f"{self.name}"

    @property
    def ports(self):
        return self._ports

    def port(self, portname):
        for port in self._ports:
            if port.name == portname:
                return port
        raise ValueError("Port not found")

    @property
    def circuit(self):
        return self._circuit

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        self._parent = parent

    def update(self):
        pass

    def add_event(self, port, level, propagation_delay_ns):
        self.circuit.add_event(port, level, propagation_delay_ns)

    def __str__(self):
        comp_str = f"{self.name}\n"
        for port in self.ports:
            comp_str += f"-{port.name}={port.bitval}\n"
        return comp_str

    @classmethod
    def from_dict(cls, circuit, json_component):
        component_name = json_component["name"]
        component_type = json_component["type"]

        py_module_name = ".".join(component_type.split(".")[0:-1])
        py_class_name = component_type.split(".")[-1]

        module = importlib.import_module(py_module_name)
        class_ = getattr(module, py_class_name)
        return class_(circuit=circuit, name=component_name)

    def to_dict(self):
        return {
            "name": self.name,
            "type": f"{type(self).__module__}.{type(self).__name__}",
        }


class MultiComponent(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self._components = []

    def add(self, component):
        self._components.append(component)
        component.parent = self
