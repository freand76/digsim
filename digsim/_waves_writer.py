from vcd import VCDWriter


class WavesWriter:
    def __init__(self, filename):
        self._vcd_name = filename
        self._vcd_file = None
        self._vcd_writer = None
        self._vcd_dict = {}

    def init(self, port_paths):
        self._vcd_file = open(self._vcd_name, mode="w", encoding="utf-8")
        self._vcd_writer = VCDWriter(self._vcd_file, timescale="1 ns", date="today")
        for port_path, port_name in port_paths:
            var = self._vcd_writer.register_var(port_path, port_name, "integer", size=1)
            self._vcd_dict[f"{port_path}.{port_name}"] = var

    def write(self, port, time_ns):
        var = self._vcd_dict[f"{port.path}.{port.name}"]
        self._vcd_writer.change(var, timestamp=time_ns, value=port.vcdval)
        for p in port.wires:
            self.write(p, time_ns)

    def close(self):
        if self._vcd_writer is not None:
            self._vcd_writer.close()
            self._vcd_writer = None

        if self._vcd_file is not None:
            self._vcd_file.close()
            self._vcd_file = None
