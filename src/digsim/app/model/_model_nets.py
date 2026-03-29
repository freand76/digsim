# Copyright (c) Fredrik Andersson, 2026
# All rights reserved

"""Handle nets in the model"""

from dataclasses import dataclass

from PySide6.QtCore import QPoint

from digsim.app.gui_objects import WireSegmentObject


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

    def get_object_list(self):
        object_list = []
        for net_name, segment_dict in self._nets.items():
            for segment_name, wire_object in segment_dict.items():
                object_list.append(wire_object)
        return object_list

    def _add_wire_object(self, net_name, segment_name, wire_object):
        if net_name not in self._nets:
            self._nets[net_name] = {}
        self._nets[net_name][segment_name] = wire_object

    def add_gui_nets(self, gui_nets):
        for net_name, gui_net in gui_nets.items():
            src_comp, src_port = self._app_model.objects.circuit.net_name_to_component_port(
                net_name
            )
            src_comp_object = self._app_model.objects.components.get_object(src_comp)
            source_port = src_comp_object.get_port_item(src_port)

            for segment in gui_net:
                if segment.parent is None:
                    parent = source_port
                else:
                    parent = self._nets[net_name][segment.parent]

                start_point = parent.point()
                end_point = None
                sink_port = None
                if segment.sink is None:
                    if segment.direction == "V":
                        end_point = QPoint(start_point.x(), start_point.y() + segment.length)
                    else:
                        end_point = QPoint(start_point.x() + segment.length, start_point.y())
                else:
                    dst_comp, dst_port = (
                        self._app_model.objects.circuit.net_name_to_component_port(segment.sink)
                    )
                    dst_comp_object = self._app_model.objects.components.get_object(dst_comp)
                    sink_port = dst_comp_object.get_port_item(dst_port)

                wire_object = WireSegmentObject(
                    self._app_model, net_name, parent, end_point, sink_port
                )
                parent.add_child(wire_object)
                if sink_port is not None:
                    sink_port.add_child(wire_object)
                self._add_wire_object(net_name, segment.name, wire_object)
