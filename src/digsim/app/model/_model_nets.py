# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Handle nets in the model"""

from dataclasses import dataclass

from PySide6.QtCore import QPoint


@dataclass
class WireSegment:
    name: str
    parent: str
    movable: bool
    start: QPoint
    end: QPoint


class ModelNets:
    """Class to handle the component objects in the model"""

    def __init__(self, app_model, circuit):
        self._app_model = app_model
        self._circuit = circuit
        self._nets = {}

    @property
    def net_dict(self):
        return self._nets

    def _add_segment(self, net_name, segment):
        if net_name not in self._nets:
            self._nets[net_name] = {}
        self._nets[net_name][segment.name] = segment

    def add_gui_nets(self, gui_nets):
        for net_name, gui_net in gui_nets.items():
            src_comp_name, src_port_name = net_name.split(".")
            src_comp = self._circuit.get_component(src_comp_name)
            src_port = src_comp.port(src_port_name)
            src_comp_object = self._app_model.objects.components.get_object(src_comp)
            src_pos = src_comp_object.get_port_item(src_port).portPos()
            for segment in gui_net:
                if segment.parent is None:
                    start_point = QPoint(int(src_pos.x()), int(src_pos.y()))
                else:
                    start_point = self._nets[net_name][segment.parent].end
                if segment.sink is None:
                    if segment.direction == "V":
                        end_point = QPoint(start_point.x(), start_point.y() + segment.length)
                    else:
                        end_point = QPoint(start_point.x() + segment.length, start_point.y())
                else:
                    dst_comp_name, dst_port_name = segment.sink.split(".")
                    dst_comp = self._circuit.get_component(dst_comp_name)
                    dst_port = dst_comp.port(dst_port_name)
                    dst_comp_object = self._app_model.objects.components.get_object(dst_comp)
                    dst_pos = dst_comp_object.get_port_item(dst_port).portPos()
                    end_point = QPoint(int(dst_pos.x()), int(dst_pos.y()))
                wire_segment = WireSegment(
                    name=segment.name,
                    parent=segment.parent,
                    movable=segment.parent is not None and segment.sink is None,
                    start=start_point,
                    end=end_point,
                )
                self._add_segment(net_name, wire_segment)
