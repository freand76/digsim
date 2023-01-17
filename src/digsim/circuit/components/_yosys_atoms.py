# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

# pylint: disable=too-many-arguments
# pylint: disable=consider-using-in

from .atoms import Component, ComponentPort, OutputPort, PortDirection, SignalLevel


class ParameterComponent(Component):
    @staticmethod
    def bool_to_level(high):
        if high:
            return SignalLevel.HIGH
        return SignalLevel.LOW


# Clock, Async Load, Enable
# module \$_ALDFFE_NNN_ (D, C, L, AD, E, Q);
# module \$_ALDFFE_NNP_ (D, C, L, AD, E, Q);
# module \$_ALDFFE_NPN_ (D, C, L, AD, E, Q);
# module \$_ALDFFE_NPP_ (D, C, L, AD, E, Q);
# module \$_ALDFFE_PNN_ (D, C, L, AD, E, Q);
# module \$_ALDFFE_PNP_ (D, C, L, AD, E, Q);
# module \$_ALDFFE_PPN_ (D, C, L, AD, E, Q);
# module \$_ALDFFE_PPP_ (D, C, L, AD, E, Q);


class _ALDFFE_(ParameterComponent):
    def __init__(self, circuit, name, pos_c, pos_l, pos_e):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self._load_level = self.bool_to_level(pos_l)
        self._enable_level = self.bool_to_level(pos_e)
        self.add_port(ComponentPort(self, "AD", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "E", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "L", PortDirection.IN))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if self.L.level == self._load_level:
            self.Q.level = self.AD.level
        elif (
            self.C.level != self._old_C_level
            and self.C.level == self._clock_edge
            and self.E.level == self._enable_level
        ):
            self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _ALDFFE_NNN_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False)


class _ALDFFE_NNP_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True)


class _ALDFFE_NPN_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False)


class _ALDFFE_NPP_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True)


class _ALDFFE_PNN_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False)


class _ALDFFE_PNP_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True)


class _ALDFFE_PPN_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False)


class _ALDFFE_PPP_(_ALDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True)


# Clock, Async Load, Enable
# module \$_ALDFF_NN_ (D, C, L, AD, Q);
# module \$_ALDFF_NP_ (D, C, L, AD, Q);
# module \$_ALDFF_PN_ (D, C, L, AD, Q);
# module \$_ALDFF_PP_ (D, C, L, AD, Q);


class _ALDFF_(ParameterComponent):
    def __init__(self, circuit, name, pos_c, pos_l):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self._load_level = self.bool_to_level(pos_l)
        self.add_port(ComponentPort(self, "AD", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "L", PortDirection.IN))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if self.L.level == self._load_level:
            self.Q.level = self.AD.level
        elif self.C.level != self._old_C_level and self.C.level == self._clock_edge:
            self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _ALDFF_NN_(_ALDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False)


class _ALDFF_NP_(_ALDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True)


class _ALDFF_PN_(_ALDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False)


class _ALDFF_PP_(_ALDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True)

        self._old_C_level = self.C.level


# module \$_DFFE_NN0N_ (D, C, R, E, Q);
# module \$_DFFE_NN0P_ (D, C, R, E, Q);
# module \$_DFFE_NN1N_ (D, C, R, E, Q);
# module \$_DFFE_NN1P_ (D, C, R, E, Q);
# module \$_DFFE_NP0N_ (D, C, R, E, Q);
# module \$_DFFE_NP0P_ (D, C, R, E, Q);
# module \$_DFFE_NP1N_ (D, C, R, E, Q);
# module \$_DFFE_NP1P_ (D, C, R, E, Q);
# module \$_DFFE_PN0N_ (D, C, R, E, Q);
# module \$_DFFE_PN0P_ (D, C, R, E, Q);
# module \$_DFFE_PN1N_ (D, C, R, E, Q);
# module \$_DFFE_PN1P_ (D, C, R, E, Q);
# module \$_DFFE_PP0N_ (D, C, R, E, Q);
# module \$_DFFE_PP0P_ (D, C, R, E, Q);
# module \$_DFFE_PP1N_ (D, C, R, E, Q);
# module \$_DFFE_PP1P_ (D, C, R, E, Q);


class _DFFE_(ParameterComponent):
    def __init__(self, circuit, name, pos_c, pos_r, r_val, pos_e):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self._reset_level = self.bool_to_level(pos_r)
        self._reset_value = self.bool_to_level(r_val)
        self._enable_level = self.bool_to_level(pos_e)
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "E", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "R", PortDirection.IN))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if self.R.level == self._reset_level:
            self.Q.level = self._reset_value
        elif (
            self.C.level != self._old_C_level
            and self.C.level == self._clock_edge
            and self.E.level == self._enable_level
        ):
            self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _DFFE_NN0N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False, False)


class _DFFE_NN0P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False, True)


class _DFFE_NN1N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True, False)


class _DFFE_NN1P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True, True)


class _DFFE_NP0N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False, False)


class _DFFE_NP0P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False, True)


class _DFFE_NP1N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True, False)


class _DFFE_NP1P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True, True)


class _DFFE_PN0N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False, False)


class _DFFE_PN0P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False, True)


class _DFFE_PN1N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True, False)


class _DFFE_PN1P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True, True)


class _DFFE_PP0N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False, False)


class _DFFE_PP0P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False, True)


class _DFFE_PP1N_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True, False)


class _DFFE_PP1P_(_DFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True, True)


# module \$_DFFE_NN_ (D, C, E, Q);
# module \$_DFFE_NP_ (D, C, E, Q);
# module \$_DFFE_PN_ (D, C, E, Q);
# module \$_DFFE_PP_ (D, C, E, Q);


class _DFFE2_(ParameterComponent):
    def __init__(self, circuit, name, pos_c, pos_e):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self._enable_level = self.bool_to_level(pos_e)
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "E", PortDirection.IN, update_parent=False))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if (
            self.C.level != self._old_C_level
            and self.C.level == self._clock_edge
            and self.E.level == self._enable_level
        ):
            self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _DFFE_NN_(_DFFE2_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False)


class _DFFE_NP_(_DFFE2_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True)


class _DFFE_PN_(_DFFE2_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False)


class _DFFE_PP_(_DFFE2_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True)


# module \$_DFF_N_ (D, C, Q);
# module \$_DFF_P_ (D, C, Q);


class _DFF_(ParameterComponent):
    def __init__(self, circuit, name, pos_c):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if self.C.level != self._old_C_level and self.C.level == self._clock_edge:
            self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _DFF_N_(_DFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False)


class _DFF_P_(_DFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True)


# module \$_DFF_NN0_ (D, C, R, Q);
# module \$_DFF_NN1_ (D, C, R, Q);
# module \$_DFF_NP0_ (D, C, R, Q);
# module \$_DFF_NP1_ (D, C, R, Q);
# module \$_DFF_PN0_ (D, C, R, Q);
# module \$_DFF_PN1_ (D, C, R, Q);
# module \$_DFF_PP0_ (D, C, R, Q);
# module \$_DFF_PP1_ (D, C, R, Q);


class _SDFF_(ParameterComponent):
    def __init__(self, circuit, name, pos_c, pos_r, r_val):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self._reset_level = self.bool_to_level(pos_r)
        self._reset_value = self.bool_to_level(r_val)
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "R", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if self.C.level != self._old_C_level and self.C.level == self._clock_edge:
            if self.R.level == self._reset_level:
                self.Q.level = self._reset_value
            else:
                self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _SDFF_NN0_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False)


class _SDFF_NN1_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True)


class _SDFF_NP0_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False)


class _SDFF_NP1_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True)


class _SDFF_PN0_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False)


class _SDFF_PN1_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True)


class _SDFF_PP0_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False)


class _SDFF_PP1_(_SDFF_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True)


# module \$_SDFF_NN0_ (D, C, R, Q);
# module \$_SDFF_NN1_ (D, C, R, Q);
# module \$_SDFF_NP0_ (D, C, R, Q);
# module \$_SDFF_NP1_ (D, C, R, Q);
# module \$_SDFF_PN0_ (D, C, R, Q);
# module \$_SDFF_PN1_ (D, C, R, Q);
# module \$_SDFF_PP0_ (D, C, R, Q);
# module \$_SDFF_PP1_ (D, C, R, Q);


# module \$_DFFSR_NNN_ (C, S, R, D, Q);
# module \$_DFFSR_NNP_ (C, S, R, D, Q);
# module \$_DFFSR_NPN_ (C, S, R, D, Q);
# module \$_DFFSR_NPP_ (C, S, R, D, Q);
# module \$_DFFSR_PNN_ (C, S, R, D, Q);
# module \$_DFFSR_PNP_ (C, S, R, D, Q);
# module \$_DFFSR_PPN_ (C, S, R, D, Q);
# module \$_DFFSR_PPP_ (C, S, R, D, Q);

# module \$_DFFSRE_NNNN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_NNNP_ (C, S, R, E, D, Q);
# module \$_DFFSRE_NNPN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_NNPP_ (C, S, R, E, D, Q);
# module \$_DFFSRE_NPNN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_NPNP_ (C, S, R, E, D, Q);
# module \$_DFFSRE_NPPN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_NPPP_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PNNN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PNNP_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PNPN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PNPP_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PPNN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PPNP_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PPPN_ (C, S, R, E, D, Q);
# module \$_DFFSRE_PPPP_ (C, S, R, E, D, Q);

# module \$_SDFFCE_NN0N_ (D, C, R, E, Q);
# module \$_SDFFCE_NN0P_ (D, C, R, E, Q);
# module \$_SDFFCE_NN1N_ (D, C, R, E, Q);
# module \$_SDFFCE_NN1P_ (D, C, R, E, Q);
# module \$_SDFFCE_NP0N_ (D, C, R, E, Q);
# module \$_SDFFCE_NP0P_ (D, C, R, E, Q);
# module \$_SDFFCE_NP1N_ (D, C, R, E, Q);
# module \$_SDFFCE_NP1P_ (D, C, R, E, Q);
# module \$_SDFFCE_PN0N_ (D, C, R, E, Q);
# module \$_SDFFCE_PN0P_ (D, C, R, E, Q);
# module \$_SDFFCE_PN1N_ (D, C, R, E, Q);
# module \$_SDFFCE_PN1P_ (D, C, R, E, Q);
# module \$_SDFFCE_PP0N_ (D, C, R, E, Q);
# module \$_SDFFCE_PP0P_ (D, C, R, E, Q);
# module \$_SDFFCE_PP1N_ (D, C, R, E, Q);
# module \$_SDFFCE_PP1P_ (D, C, R, E, Q);


class _SDFFCE_(ParameterComponent):
    def __init__(self, circuit, name, pos_c, pos_r, r_val, pos_e):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self._reset_level = self.bool_to_level(pos_r)
        self._reset_value = self.bool_to_level(r_val)
        self._enable_level = self.bool_to_level(pos_e)
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "E", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "R", PortDirection.IN, update_parent=False))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level
        self.Q.level = SignalLevel.LOW

    def update(self):
        if self.C.level != self._old_C_level and self.C.level == self._clock_edge:
            if self.E.level == self._enable_level:
                if self.R.level == self._reset_level:
                    self.Q.level = self._reset_value
                else:
                    self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _SDFFCE_NN0N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False, False)


class _SDFFCE_NN0P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False, True)


class _SDFFCE_NN1N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True, False)


class _SDFFCE_NN1P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True, True)


class _SDFFCE_NP0N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False, False)


class _SDFFCE_NP0P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False, True)


class _SDFFCE_NP1N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True, False)


class _SDFFCE_NP1P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True, True)


class _SDFFCE_PN0N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False, False)


class _SDFFCE_PN0P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False, True)


class _SDFFCE_PN1N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True, False)


class _SDFFCE_PN1P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True, True)


class _SDFFCE_PP0N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False, False)


class _SDFFCE_PP0P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False, True)


class _SDFFCE_PP1N_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True, False)


class _SDFFCE_PP1P_(_SDFFCE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True, True)


# module \$_SDFFE_NN0N_ (D, C, R, E, Q);
# module \$_SDFFE_NN0P_ (D, C, R, E, Q);
# module \$_SDFFE_NN1N_ (D, C, R, E, Q);
# module \$_SDFFE_NN1P_ (D, C, R, E, Q);
# module \$_SDFFE_NP0N_ (D, C, R, E, Q);
# module \$_SDFFE_NP0P_ (D, C, R, E, Q);
# module \$_SDFFE_NP1N_ (D, C, R, E, Q);
# module \$_SDFFE_NP1P_ (D, C, R, E, Q);
# module \$_SDFFE_PN0N_ (D, C, R, E, Q);
# module \$_SDFFE_PN0P_ (D, C, R, E, Q);
# module \$_SDFFE_PN1N_ (D, C, R, E, Q);
# module \$_SDFFE_PN1P_ (D, C, R, E, Q);
# module \$_SDFFE_PP0N_ (D, C, R, E, Q);
# module \$_SDFFE_PP0P_ (D, C, R, E, Q);
# module \$_SDFFE_PP1N_ (D, C, R, E, Q);
# module \$_SDFFE_PP1P_ (D, C, R, E, Q);


class _SDFFE_(ParameterComponent):
    def __init__(self, circuit, name, pos_c, pos_r, r_val, pos_e):
        super().__init__(circuit, name)
        self._clock_edge = self.bool_to_level(pos_c)
        self._reset_level = self.bool_to_level(pos_r)
        self._reset_value = self.bool_to_level(r_val)
        self._enable_level = self.bool_to_level(pos_e)
        self.add_port(ComponentPort(self, "C", PortDirection.IN))
        self.add_port(ComponentPort(self, "D", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "E", PortDirection.IN, update_parent=False))
        self.add_port(ComponentPort(self, "R", PortDirection.IN, update_parent=False))
        self.add_port(OutputPort(self, "Q"))
        self._old_C_level = self.C.level

    def update(self):
        if self.C.level != self._old_C_level and self.C.level == self._clock_edge:
            if self.R.level == self._reset_level:
                self.Q.level = self._reset_value
            elif self.E.level == self._enable_level:
                self.Q.level = self.D.level
        self._old_C_level = self.C.level


class _SDFFE_NN0N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False, False)


class _SDFFE_NN0P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, False, True)


class _SDFFE_NN1N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True, False)


class _SDFFE_NN1P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, False, True, True)


class _SDFFE_NP0N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False, False)


class _SDFFE_NP0P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, False, True)


class _SDFFE_NP1N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True, False)


class _SDFFE_NP1P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, False, True, True, True)


class _SDFFE_PN0N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False, False)


class _SDFFE_PN0P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, False, True)


class _SDFFE_PN1N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True, False)


class _SDFFE_PN1P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, False, True, True)


class _SDFFE_PP0N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False, False)


class _SDFFE_PP0P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, False, True)


class _SDFFE_PP1N_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True, False)


class _SDFFE_PP1P_(_SDFFE_):
    def __init__(self, circuit, name):
        super().__init__(circuit, name, True, True, True, True)


# module \$_DLATCH_N_ (E, D, Q);
# module \$_DLATCH_P_ (E, D, Q);

# module \$_DLATCH_NN0_ (E, R, D, Q);
# module \$_DLATCH_NN1_ (E, R, D, Q);
# module \$_DLATCH_NP0_ (E, R, D, Q);
# module \$_DLATCH_NP1_ (E, R, D, Q);
# module \$_DLATCH_PN0_ (E, R, D, Q);
# module \$_DLATCH_PN1_ (E, R, D, Q);
# module \$_DLATCH_PP0_ (E, R, D, Q);
# module \$_DLATCH_PP1_ (E, R, D, Q);

# module \$_DLATCHSR_NNN_ (E, S, R, D, Q);
# module \$_DLATCHSR_NNP_ (E, S, R, D, Q);
# module \$_DLATCHSR_NPN_ (E, S, R, D, Q);
# module \$_DLATCHSR_NPP_ (E, S, R, D, Q);
# module \$_DLATCHSR_PNN_ (E, S, R, D, Q);
# module \$_DLATCHSR_PNP_ (E, S, R, D, Q);
# module \$_DLATCHSR_PPN_ (E, S, R, D, Q);
# module \$_DLATCHSR_PPP_ (E, S, R, D, Q);

# module \$_SR_NN_ (S, R, Q);
# module \$_SR_NP_ (S, R, Q);
# module \$_SR_PN_ (S, R, Q);
# module \$_SR_PP_ (S, R, Q);

# module \$_NMUX_ (A, B, S, Y);
# module \$_MUX_ (A, B, S, Y);


class _MUX_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(ComponentPort(self, "S", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.S.level == SignalLevel.LOW:
            self.Y.level = self.A.level
        else:
            self.Y.level = self.B.level


# module \$_MUX16_ (A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, S, T, U, V, Y);
# module \$_MUX4_ (A, B, C, D, S, T, Y);
# module \$_MUX8_ (A, B, C, D, E, F, G, H, S, T, U, Y);

# module \$_AND_ (A, B, Y);


class _AND_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.HIGH
        else:
            self.Y.level = SignalLevel.LOW


# module \$_ANDNOT_ (A, B, Y);


class _ANDNOT_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.LOW:
            self.Y.level = SignalLevel.HIGH
        else:
            self.Y.level = SignalLevel.LOW


# module \$_BUF_ (A, Y);
# module \$_FF_ (D, Q);
# module \$_NAND_ (A, B, Y);


class _NAND_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.LOW
        else:
            self.Y.level = SignalLevel.HIGH


# module \$_NOR_ (A, B, Y);


class _NOR_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH or self.B.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.LOW
        else:
            self.Y.level = SignalLevel.HIGH


# module \$_NOT_ (A, Y);


class _NOT_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.LOW
        else:
            self.Y.level = SignalLevel.HIGH


# module \$_OR_ (A, B, Y);


class _OR_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH or self.B.level == SignalLevel.HIGH:
            self.Y.level = SignalLevel.HIGH
        else:
            self.Y.level = SignalLevel.LOW


# module \$_ORNOT_ (A, B, Y);


class _ORNOT_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if self.A.level == SignalLevel.HIGH or self.B.level == SignalLevel.LOW:
            self.Y.level = SignalLevel.HIGH
        else:
            self.Y.level = SignalLevel.LOW


# module \$_AOI3_ (A, B, C, Y);
# module \$_AOI4_ (A, B, C, D, Y);
# module \$_OAI3_ (A, B, C, Y);
# module \$_OAI4_ (A, B, C, D, Y);
# module \$_TBUF_ (A, E, Y);
# module \$_XNOR_ (A, B, Y);
class _XNOR_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if (self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.LOW) or (
            self.A.level == SignalLevel.LOW and self.B.level == SignalLevel.HIGH
        ):
            self.Y.level = SignalLevel.LOW
        else:
            self.Y.level = SignalLevel.HIGH


# module \$_XOR_ (A, B, Y);
class _XOR_(Component):
    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "A", PortDirection.IN))
        self.add_port(ComponentPort(self, "B", PortDirection.IN))
        self.add_port(OutputPort(self, "Y"))

    def update(self):
        if (self.A.level == SignalLevel.HIGH and self.B.level == SignalLevel.LOW) or (
            self.A.level == SignalLevel.LOW and self.B.level == SignalLevel.HIGH
        ):
            self.Y.level = SignalLevel.HIGH
        else:
            self.Y.level = SignalLevel.LOW
