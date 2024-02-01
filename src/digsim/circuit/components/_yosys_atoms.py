# Copyright (c) Fredrik Andersson, 2023-2024
# All rights reserved

"""
Module with yosys atom component classes

All components are implemented from the specification in:
https://github.com/YosysHQ/yosys/blob/master/techlibs/common/simcells.v
"""

from .atoms import Component, DigsimException, PortIn, PortOutDelta, PortWire


class YosysNotImplementedException(DigsimException):
    """Exception for not implemented components"""


class ClassNameParameterComponent(Component):
    """
    Helper class to get active level and edges from class name
    """

    def name_to_level(self, index):
        """
        Helper function to convert a specific position in the class name
        to a logic level:
        N/0 ==> 0
        P/1 ==> 1
        """
        class_name = self.__class__.__name__
        split = class_name.split("_")
        level = split[2][index]
        if level in ["N", "0"]:
            return 0
        if level in ["P", "1"]:
            return 1
        raise ValueError(f"Unknown value ä{level}'")


class _BUF_(Component):
    """module _BUF_ (A, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        self.Y.value = self.A.value


class _NOT_(Component):
    """module _NOT_ (A, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == 1:
            self.Y.value = 0
        else:
            self.Y.value = 1


class _AND_(Component):
    """module _AND_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == 1 and self.B.value == 1:
            self.Y.value = 1
        else:
            self.Y.value = 0


class _NAND_(Component):
    """module _NAND_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == 1 and self.B.value == 1:
            self.Y.value = 0
        else:
            self.Y.value = 1


class _OR_(Component):
    """module _OR_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == 1 or self.B.value == 1:
            self.Y.value = 1
        else:
            self.Y.value = 0


class _NOR_(Component):
    """module _NOR_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == 1 or self.B.value == 1:
            self.Y.value = 0
        else:
            self.Y.value = 1


class _XOR_(Component):
    """module _XOR_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if (self.A.value == 1 and self.B.value == 0) or (self.A.value == 0 and self.B.value == 1):
            self.Y.value = 1
        else:
            self.Y.value = 0


class _XNOR_(Component):
    """module _XNOR_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if (self.A.value == 1 and self.B.value == 0) or (self.A.value == 0 and self.B.value == 1):
            self.Y.value = 0
        else:
            self.Y.value = 1


class _ANDNOT_(Component):
    """module _ANDNOT_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == 1 and self.B.value == 0:
            self.Y.value = 1
        else:
            self.Y.value = 0


class _ORNOT_(Component):
    """module _ORNOT_ (A, B, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.A.value == 1 or self.B.value == 0:
            self.Y.value = 1
        else:
            self.Y.value = 0


class _MUX_(Component):
    """module _MUX_ (A, B, S, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.S.value == 0:
            self.Y.value = self.A.value
        else:
            self.Y.value = self.B.value


class _NMUX_(Component):
    """module _NMUX_ (A, B, S, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.S.value == 0:
            self.Y.value = 1 if self.A.value == 0 else 0
        else:
            self.Y.value = 1 if self.B.value == 0 else 0


class _MUX4_(Component):
    """module _MUX4_ (A, B, C, D, S, T, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortIn(self, "T"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.S.value == 0 and self.T.value == 0:
            self.Y.value = self.A.value
        elif self.S.value == 1 and self.T.value == 0:
            self.Y.value = self.B.value
        elif self.S.value == 0 and self.T.value == 1:
            self.Y.value = self.C.value
        else:
            self.Y.value = self.D.value


class _MUX8_(Component):
    """module _MUX8_ (A, B, C, D, E, F, G, H, S, T, U, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortIn(self, "E"))
        self.add_port(PortIn(self, "F"))
        self.add_port(PortIn(self, "G"))
        self.add_port(PortIn(self, "H"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortIn(self, "T"))
        self.add_port(PortIn(self, "U"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.S.value == 0 and self.T.value == 0 and self.U.value == 0:
            self.Y.value = self.A.value
        elif self.S.value == 1 and self.T.value == 0 and self.U.value == 0:
            self.Y.value = self.B.value
        elif self.S.value == 0 and self.T.value == 1 and self.U.value == 0:
            self.Y.value = self.C.value
        elif self.S.value == 1 and self.T.value == 1 and self.U.value == 0:
            self.Y.value = self.D.value
        elif self.S.value == 0 and self.T.value == 0 and self.U.value == 1:
            self.Y.value = self.E.value
        elif self.S.value == 1 and self.T.value == 0 and self.U.value == 1:
            self.Y.value = self.F.value
        elif self.S.value == 0 and self.T.value == 1 and self.U.value == 1:
            self.Y.value = self.G.value
        else:
            self.Y.value = self.H.value


class _MUX16_(Component):
    """module _MUX16_ (A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, S, T, U, V, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortIn(self, "E"))
        self.add_port(PortIn(self, "F"))
        self.add_port(PortIn(self, "G"))
        self.add_port(PortIn(self, "H"))
        self.add_port(PortIn(self, "I"))
        self.add_port(PortIn(self, "J"))
        self.add_port(PortIn(self, "K"))
        self.add_port(PortIn(self, "L"))
        self.add_port(PortIn(self, "M"))
        self.add_port(PortIn(self, "N"))
        self.add_port(PortIn(self, "O"))
        self.add_port(PortIn(self, "P"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortIn(self, "T"))
        self.add_port(PortIn(self, "U"))
        self.add_port(PortIn(self, "V"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if self.S.value == 0 and self.T.value == 0 and self.U.value == 0 and self.V.value == 0:
            self.Y.value = self.A.value
        elif self.S.value == 1 and self.T.value == 0 and self.U.value == 0 and self.V.value == 0:
            self.Y.value = self.B.value
        elif self.S.value == 0 and self.T.value == 1 and self.U.value == 0 and self.V.value == 0:
            self.Y.value = self.C.value
        elif self.S.value == 1 and self.T.value == 1 and self.U.value == 0 and self.V.value == 0:
            self.Y.value = self.D.value
        elif self.S.value == 0 and self.T.value == 0 and self.U.value == 1 and self.V.value == 0:
            self.Y.value = self.E.value
        elif self.S.value == 1 and self.T.value == 0 and self.U.value == 1 and self.V.value == 0:
            self.Y.value = self.F.value
        elif self.S.value == 0 and self.T.value == 1 and self.U.value == 1 and self.V.value == 0:
            self.Y.value = self.G.value
        elif self.S.value == 1 and self.T.value == 1 and self.U.value == 1 and self.V.value == 0:
            self.Y.value = self.H.value
        elif self.S.value == 0 and self.T.value == 0 and self.U.value == 0 and self.V.value == 1:
            self.Y.value = self.I.value
        elif self.S.value == 1 and self.T.value == 0 and self.U.value == 0 and self.V.value == 1:
            self.Y.value = self.J.value
        elif self.S.value == 0 and self.T.value == 1 and self.U.value == 0 and self.V.value == 1:
            self.Y.value = self.K.value
        elif self.S.value == 1 and self.T.value == 1 and self.U.value == 0 and self.V.value == 1:
            self.Y.value = self.L.value
        elif self.S.value == 0 and self.T.value == 0 and self.U.value == 1 and self.V.value == 1:
            self.Y.value = self.M.value
        elif self.S.value == 1 and self.T.value == 0 and self.U.value == 1 and self.V.value == 1:
            self.Y.value = self.N.value
        elif self.S.value == 0 and self.T.value == 1 and self.U.value == 1 and self.V.value == 1:
            self.Y.value = self.O.value
        else:
            self.Y.value = self.P.value


class _AOI3_(Component):
    """module _AOI3_ (A, B, C, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if (self.A.value == 1 and self.B.value == 1) or self.C.value == 1:
            self.Y.value = 0
        else:
            self.Y.value = 1


class _OAI3_(Component):
    """module _OAI3_ (A, B, C, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if (self.A.value == 1 or self.B.value == 1) and self.C.value == 1:
            self.Y.value = 0
        else:
            self.Y.value = 1


class _AOI4_(Component):
    """module _AOI4_ (A, B, C, D, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if (self.A.value == 1 and self.B.value == 1) or (self.C.value == 1 and self.D.value == 1):
            self.Y.value = 0
        else:
            self.Y.value = 1


class _OAI4_(Component):
    """module _OAI4_ (A, B, C, D, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortIn(self, "A"))
        self.add_port(PortIn(self, "B"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortOutDelta(self, "Y"))

    def update(self):
        if (self.A.value == 1 or self.B.value == 1) and (self.C.value == 1 or self.D.value == 1):
            self.Y.value = 0
        else:
            self.Y.value = 1


class _TBUF_(Component):
    """module _TBUF_ (A, E, Y)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        raise YosysNotImplementedException("NOT IMPLEMENTED: Tri-state buffer")


class _SR_(ClassNameParameterComponent):
    """Set-reset latch"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._set_level = self.name_to_level(0)
        self._reset_level = self.name_to_level(1)
        self.add_port(PortIn(self, "S"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortOutDelta(self, "Q"))

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.R.value == self._reset_level:
            self.Q.value = 0
        elif self.S.value == self._set_level:
            self.Q.value = 1


class _SR_NN_(_SR_):
    """module _SR_NN_ (S, R, Q)"""


class _SR_NP_(_SR_):
    """module _SR_NP_ (S, R, Q)"""


class _SR_PN_(_SR_):
    """module _SR_PN_ (S, R, Q)"""


class _SR_PP_(_SR_):
    """module _SR_PP_ (S, R, Q)"""


class _FF_(Component):
    """module module _FF_ (D, Q)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        raise YosysNotImplementedException(
            "NOT IMPLEMENTED: D-type flip-flop that is clocked from the implicit global clock"
        )


class _DFF_(ClassNameParameterComponent):
    """D-type flip-flop"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.C.value != self._old_C_level and self.C.value == self._clock_edge:
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _DFF_N_(_DFF_):
    """module _DFF_N_ (D, C, Q)"""


class _DFF_P_(_DFF_):
    """module _DFF_P_ (D, C, Q)"""


class _DFFE2_(ClassNameParameterComponent):
    """D-type flip-flop with clock enable"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._enable_level = self.name_to_level(1)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortWire(self, "E"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if (
            self.C.value != self._old_C_level
            and self.C.value == self._clock_edge
            and self.E.value == self._enable_level
        ):
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _DFFE_NN_(_DFFE2_):
    """module _DFFE_NN_ (D, C, E, Q)"""


class _DFFE_NP_(_DFFE2_):
    """module _DFFE_NP_ (D, C, E, Q)"""


class _DFFE_PN_(_DFFE2_):
    """module _DFFE_PN_ (D, C, E, Q)"""


class _DFFE_PP_(_DFFE2_):
    """module _DFFE_PP_ (D, C, E, Q)"""


class _DFF3_(ClassNameParameterComponent):
    """D-type flip-flop with reset"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._reset_level = self.name_to_level(1)
        self._reset_value = self.name_to_level(2)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.R.value == self._reset_level:
            self.Q.value = self._reset_value
        elif self.C.value != self._old_C_level and self.C.value == self._clock_edge:
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _DFF_NN0_(_DFF3_):
    """module _DFF_NN0_ (D, C, R, Q)"""


class _DFF_NN1_(_DFF3_):
    """module _DFF_NN1_ (D, C, R, Q)"""


class _DFF_NP0_(_DFF3_):
    """module _DFF_NP0_ (D, C, R, Q)"""


class _DFF_NP1_(_DFF3_):
    """module _DFF_NP1_ (D, C, R, Q)"""


class _DFF_PN0_(_DFF3_):
    """module _DFF_PN0_ (D, C, R, Q)"""


class _DFF_PN1_(_DFF3_):
    """module _DFF_PN1_ (D, C, R, Q)"""


class _DFF_PP0_(_DFF3_):
    """module _DFF_PP0_ (D, C, R, Q)"""


class _DFF_PP1_(_DFF3_):
    """module _DFF_PP1_ (D, C, R, Q)"""


class _DFFE4_(ClassNameParameterComponent):
    """D-type flip-flop with reset and clock enable"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._reset_level = self.name_to_level(1)
        self._reset_value = self.name_to_level(2)
        self._enable_level = self.name_to_level(3)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortWire(self, "E"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.R.value == self._reset_level:
            self.Q.value = self._reset_value
        elif (
            self.C.value != self._old_C_level
            and self.C.value == self._clock_edge
            and self.E.value == self._enable_level
        ):
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _DFFE_NN0N_(_DFFE4_):
    """module _DFFE_NN0N_ (D, C, R, E, Q)"""


class _DFFE_NN0P_(_DFFE4_):
    """module _DFFE_NN0P_ (D, C, R, E, Q)"""


class _DFFE_NN1N_(_DFFE4_):
    """module _DFFE_NN1N_ (D, C, R, E, Q)"""


class _DFFE_NN1P_(_DFFE4_):
    """module _DFFE_NN1P_ (D, C, R, E, Q)"""


class _DFFE_NP0N_(_DFFE4_):
    """module _DFFE_NP0N_ (D, C, R, E, Q)"""


class _DFFE_NP0P_(_DFFE4_):
    """module _DFFE_NP0P_ (D, C, R, E, Q)"""


class _DFFE_NP1N_(_DFFE4_):
    """module _DFFE_NP1N_ (D, C, R, E, Q)"""


class _DFFE_NP1P_(_DFFE4_):
    """module _DFFE_NP1P_ (D, C, R, E, Q)"""


class _DFFE_PN0N_(_DFFE4_):
    """module _DFFE_PN0N_ (D, C, R, E, Q)"""


class _DFFE_PN0P_(_DFFE4_):
    """module _DFFE_PN0P_ (D, C, R, E, Q)"""


class _DFFE_PN1N_(_DFFE4_):
    """module _DFFE_PN1N_ (D, C, R, E, Q)"""


class _DFFE_PN1P_(_DFFE4_):
    """module _DFFE_PN1P_ (D, C, R, E, Q)"""


class _DFFE_PP0N_(_DFFE4_):
    """module _DFFE_PP0N_ (D, C, R, E, Q)"""


class _DFFE_PP0P_(_DFFE4_):
    """module _DFFE_PP0P_ (D, C, R, E, Q)"""


class _DFFE_PP1N_(_DFFE4_):
    """module _DFFE_PP1N_ (D, C, R, E, Q)"""


class _DFFE_PP1P_(_DFFE4_):
    """module _DFFE_PP1P_ (D, C, R, E, Q)"""


class _ALDFF_(ClassNameParameterComponent):
    """D-type flip-flop with async load"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._load_level = self.name_to_level(1)
        self.add_port(PortWire(self, "AD"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortIn(self, "L"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.L.value == self._load_level:
            self.Q.value = self.AD.value
        elif self.C.value != self._old_C_level and self.C.value == self._clock_edge:
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _ALDFF_NN_(_ALDFF_):
    """module _ALDFF_NN_ (D, C, L, AD, Q)"""


class _ALDFF_NP_(_ALDFF_):
    """module _ALDFF_NP_ (D, C, L, AD, Q)"""


class _ALDFF_PN_(_ALDFF_):
    """module _ALDFF_PN_ (D, C, L, AD, Q)"""


class _ALDFF_PP_(_ALDFF_):
    """module _ALDFF_PP_ (D, C, L, AD, Q)"""


class _ALDFFE_(ClassNameParameterComponent):
    """D-type flip-flop with async load and clock enable"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._load_level = self.name_to_level(1)
        self._enable_level = self.name_to_level(2)
        self.add_port(PortWire(self, "AD"))
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortWire(self, "E"))
        self.add_port(PortIn(self, "L"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = self._reset_level

    def update(self):
        if self.L.value == self._load_level:
            self.Q.value = self.AD.value
        elif (
            self.C.value != self._old_C_level
            and self.C.value == self._clock_edge
            and self.E.value == self._enable_level
        ):
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _ALDFFE_NNN_(_ALDFFE_):
    """module _ALDFFE_NNN_ (D, C, L, AD, E, Q)"""


class _ALDFFE_NNP_(_ALDFFE_):
    """module _ALDFFE_NNP_ (D, C, L, AD, E, Q)"""


class _ALDFFE_NPN_(_ALDFFE_):
    """module _ALDFFE_NPN_ (D, C, L, AD, E, Q)"""


class _ALDFFE_NPP_(_ALDFFE_):
    """module _ALDFFE_NPP_ (D, C, L, AD, E, Q)"""


class _ALDFFE_PNN_(_ALDFFE_):
    """module _ALDFFE_PNN_ (D, C, L, AD, E, Q)"""


class _ALDFFE_PNP_(_ALDFFE_):
    """module _ALDFFE_PNP_ (D, C, L, AD, E, Q)"""


class _ALDFFE_PPN_(_ALDFFE_):
    """module _ALDFFE_PPN_ (D, C, L, AD, E, Q)"""


class _ALDFFE_PPP_(_ALDFFE_):
    """module _ALDFFE_PPP_ (D, C, L, AD, E, Q)"""


class _DFFSR_(ClassNameParameterComponent):
    """D-type flip-flop with with set and reset"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._set_level = self.name_to_level(1)
        self._reset_level = self.name_to_level(2)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.R.value == self._reset_level:
            self.Q.value = 0
        elif self.S.value == self._set_level:
            self.Q.value = 1
        elif self.C.value != self._old_C_level and self.C.value == self._clock_edge:
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _DFFSR_NNN_(_DFFSR_):
    """module _DFFSR_NNN_ (C, S, R, D, Q)"""


class _DFFSR_NNP_(_DFFSR_):
    """module _DFFSR_NNP_ (C, S, R, D, Q)"""


class _DFFSR_NPN_(_DFFSR_):
    """module _DFFSR_NPN_ (C, S, R, D, Q)"""


class _DFFSR_NPP_(_DFFSR_):
    """module _DFFSR_NPP_ (C, S, R, D, Q)"""


class _DFFSR_PNN_(_DFFSR_):
    """module _DFFSR_PNN_ (C, S, R, D, Q)"""


class _DFFSR_PNP_(_DFFSR_):
    """module _DFFSR_PNP_ (C, S, R, D, Q)"""


class _DFFSR_PPN_(_DFFSR_):
    """module _DFFSR_PPN_ (C, S, R, D, Q)"""


class _DFFSR_PPP_(_DFFSR_):
    """module _DFFSR_PPP_ (C, S, R, D, Q)"""


class _DFFSRE_(ClassNameParameterComponent):
    """D-type flip-flop with with set, reset and clock enable"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._set_level = self.name_to_level(1)
        self._reset_level = self.name_to_level(2)
        self._enable_level = self.name_to_level(3)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortWire(self, "E"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.R.value == self._reset_level:
            self.Q.value = 0
        elif self.S.value == self._set_level:
            self.Q.value = 1
        elif (
            self.C.value != self._old_C_level
            and self.C.value == self._clock_edge
            and self.E.value == self._enable_level
        ):
            self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _DFFSRE_NNNN_(_DFFSRE_):
    """module _DFFSRE_NNNN_ (C, S, R, E, D, Q)"""


class _DFFSRE_NNNP_(_DFFSRE_):
    """module _DFFSRE_NNNP_ (C, S, R, E, D, Q)"""


class _DFFSRE_NNPN_(_DFFSRE_):
    """module _DFFSRE_NNPN_ (C, S, R, E, D, Q)"""


class _DFFSRE_NNPP_(_DFFSRE_):
    """module _DFFSRE_NNPP_ (C, S, R, E, D, Q)"""


class _DFFSRE_NPNN_(_DFFSRE_):
    """module _DFFSRE_NPNN_ (C, S, R, E, D, Q)"""


class _DFFSRE_NPNP_(_DFFSRE_):
    """module _DFFSRE_NPNP_ (C, S, R, E, D, Q)"""


class _DFFSRE_NPPN_(_DFFSRE_):
    """module _DFFSRE_NPPN_ (C, S, R, E, D, Q)"""


class _DFFSRE_NPPP_(_DFFSRE_):
    """module _DFFSRE_NPPP_ (C, S, R, E, D, Q)"""


class _DFFSRE_PNNN_(_DFFSRE_):
    """module _DFFSRE_PNNN_ (C, S, R, E, D, Q)"""


class _DFFSRE_PNNP_(_DFFSRE_):
    """module _DFFSRE_PNNP_ (C, S, R, E, D, Q)"""


class _DFFSRE_PNPN_(_DFFSRE_):
    """module _DFFSRE_PNPN_ (C, S, R, E, D, Q)"""


class _DFFSRE_PNPP_(_DFFSRE_):
    """module _DFFSRE_PNPP_ (C, S, R, E, D, Q)"""


class _DFFSRE_PPNN_(_DFFSRE_):
    """module _DFFSRE_PPNN_ (C, S, R, E, D, Q)"""


class _DFFSRE_PPNP_(_DFFSRE_):
    """module _DFFSRE_PPNP_ (C, S, R, E, D, Q)"""


class _DFFSRE_PPPN_(_DFFSRE_):
    """module _DFFSRE_PPPN_ (C, S, R, E, D, Q)"""


class _DFFSRE_PPPP_(_DFFSRE_):
    """module _DFFSRE_PPPP_ (C, S, R, E, D, Q)"""


class _SDFF_(ClassNameParameterComponent):
    """D-type flip-flop with sync reset"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._reset_level = self.name_to_level(1)
        self._reset_value = self.name_to_level(2)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "R"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.C.value != self._old_C_level and self.C.value == self._clock_edge:
            if self.R.value == self._reset_level:
                self.Q.value = self._reset_value
            else:
                self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _SDFF_NN0_(_SDFF_):
    """module _SDFF_NN0_ (D, C, R, Q)"""


class _SDFF_NN1_(_SDFF_):
    """module _SDFF_NN1_ (D, C, R, Q)"""


class _SDFF_NP0_(_SDFF_):
    """module _SDFF_NP0_ (D, C, R, Q)"""


class _SDFF_NP1_(_SDFF_):
    """module _SDFF_NP1_ (D, C, R, Q)"""


class _SDFF_PN0_(_SDFF_):
    """module _SDFF_PN0_ (D, C, R, Q)"""


class _SDFF_PN1_(_SDFF_):
    """module _SDFF_PN1_ (D, C, R, Q)"""


class _SDFF_PP0_(_SDFF_):
    """module _SDFF_PP0_ (D, C, R, Q)"""


class _SDFF_PP1_(_SDFF_):
    """module _SDFF_PP1_ (D, C, R, Q)"""


class _SDFFE_(ClassNameParameterComponent):
    """D-type flip-flop with sync reset and clock enable (with reset having priority)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._reset_level = self.name_to_level(1)
        self._reset_value = self.name_to_level(2)
        self._enable_level = self.name_to_level(3)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortWire(self, "E"))
        self.add_port(PortWire(self, "R"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.C.value != self._old_C_level and self.C.value == self._clock_edge:
            if self.R.value == self._reset_level:
                self.Q.value = self._reset_value
            elif self.E.value == self._enable_level:
                self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _SDFFE_NN0N_(_SDFFE_):
    """module _SDFFE_NN0N_ (D, C, R, E, Q)"""


class _SDFFE_NN0P_(_SDFFE_):
    """module _SDFFE_NN0P_ (D, C, R, E, Q)"""


class _SDFFE_NN1N_(_SDFFE_):
    """module _SDFFE_NN1N_ (D, C, R, E, Q)"""


class _SDFFE_NN1P_(_SDFFE_):
    """module _SDFFE_NN1P_ (D, C, R, E, Q)"""


class _SDFFE_NP0N_(_SDFFE_):
    """module _SDFFE_NP0N_ (D, C, R, E, Q)"""


class _SDFFE_NP0P_(_SDFFE_):
    """module _SDFFE_NP0P_ (D, C, R, E, Q)"""


class _SDFFE_NP1N_(_SDFFE_):
    """module _SDFFE_NP1N_ (D, C, R, E, Q)"""


class _SDFFE_NP1P_(_SDFFE_):
    """module _SDFFE_NP1P_ (D, C, R, E, Q)"""


class _SDFFE_PN0N_(_SDFFE_):
    """module _SDFFE_PN0N_ (D, C, R, E, Q)"""


class _SDFFE_PN0P_(_SDFFE_):
    """module _SDFFE_PN0P_ (D, C, R, E, Q)"""


class _SDFFE_PN1N_(_SDFFE_):
    """module _SDFFE_PN1N_ (D, C, R, E, Q)"""


class _SDFFE_PN1P_(_SDFFE_):
    """module _SDFFE_PN1P_ (D, C, R, E, Q)"""


class _SDFFE_PP0N_(_SDFFE_):
    """module _SDFFE_PP0N_ (D, C, R, E, Q)"""


class _SDFFE_PP0P_(_SDFFE_):
    """module _SDFFE_PP0P_ (D, C, R, E, Q)"""


class _SDFFE_PP1N_(_SDFFE_):
    """module _SDFFE_PP1N_ (D, C, R, E, Q)"""


class _SDFFE_PP1P_(_SDFFE_):
    """module _SDFFE_PP1P_ (D, C, R, E, Q)"""


class _SDFFCE_(ClassNameParameterComponent):
    """D-type flip-flop with sync reset and clock enable (with clock enable having priority)"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._clock_edge = self.name_to_level(0)
        self._reset_level = self.name_to_level(1)
        self._reset_value = self.name_to_level(2)
        self._enable_level = self.name_to_level(3)
        self.add_port(PortIn(self, "C"))
        self.add_port(PortWire(self, "D"))
        self.add_port(PortWire(self, "E"))
        self.add_port(PortWire(self, "R"))
        self.add_port(PortOutDelta(self, "Q"))
        self._old_C_level = self.C.value

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.C.value != self._old_C_level and self.C.value == self._clock_edge:
            if self.E.value == self._enable_level:
                if self.R.value == self._reset_level:
                    self.Q.value = self._reset_value
                else:
                    self.Q.value = self.D.value
        self._old_C_level = self.C.value


class _SDFFCE_NN0N_(_SDFFCE_):
    """module _SDFFCE_NN0N_ (D, C, R, E, Q)"""


class _SDFFCE_NN0P_(_SDFFCE_):
    """module _SDFFCE_NN0P_ (D, C, R, E, Q)"""


class _SDFFCE_NN1N_(_SDFFCE_):
    """module _SDFFCE_NN1N_ (D, C, R, E, Q)"""


class _SDFFCE_NN1P_(_SDFFCE_):
    """module _SDFFCE_NN1P_ (D, C, R, E, Q)"""


class _SDFFCE_NP0N_(_SDFFCE_):
    """module _SDFFCE_NP0N_ (D, C, R, E, Q)"""


class _SDFFCE_NP0P_(_SDFFCE_):
    """module _SDFFCE_NP0P_ (D, C, R, E, Q)"""


class _SDFFCE_NP1N_(_SDFFCE_):
    """module _SDFFCE_NP1N_ (D, C, R, E, Q)"""


class _SDFFCE_NP1P_(_SDFFCE_):
    """module _SDFFCE_NP1P_ (D, C, R, E, Q)"""


class _SDFFCE_PN0N_(_SDFFCE_):
    """module _SDFFCE_PN0N_ (D, C, R, E, Q)"""


class _SDFFCE_PN0P_(_SDFFCE_):
    """module _SDFFCE_PN0P_ (D, C, R, E, Q)"""


class _SDFFCE_PN1N_(_SDFFCE_):
    """module _SDFFCE_PN1N_ (D, C, R, E, Q)"""


class _SDFFCE_PN1P_(_SDFFCE_):
    """module _SDFFCE_PN1P_ (D, C, R, E, Q)"""


class _SDFFCE_PP0N_(_SDFFCE_):
    """module _SDFFCE_PP0N_ (D, C, R, E, Q)"""


class _SDFFCE_PP0P_(_SDFFCE_):
    """module _SDFFCE_PP0P_ (D, C, R, E, Q)"""


class _SDFFCE_PP1N_(_SDFFCE_):
    """module _SDFFCE_PP1N_ (D, C, R, E, Q)"""


class _SDFFCE_PP1P_(_SDFFCE_):
    """module _SDFFCE_PP1P_ (D, C, R, E, Q)"""


class _DLATCH_(ClassNameParameterComponent):
    """D-type latch"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._enable_level = self.name_to_level(0)
        self.add_port(PortIn(self, "E"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.E.value == self._enable_level:
            self.Q.value = self.D.value


class _DLATCH_N_(_DLATCH_):
    """module _DLATCH_N_ (E, D, Q)"""


class _DLATCH_P_(_DLATCH_):
    """module _DLATCH_P_ (E, D, Q)"""


class _DLATCH3_(ClassNameParameterComponent):
    """D-type latch with reset"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._enable_level = self.name_to_level(0)
        self._reset_level = self.name_to_level(1)
        self._reset_value = self.name_to_level(2)
        self.add_port(PortIn(self, "E"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.R.value == self._reset_level:
            self.Q.value = self._reset_value
        elif self.E.value == self._enable_level:
            self.Q.value = self.D.value


class _DLATCH_NN0_(_DLATCH3_):
    """module _DLATCH_NN0_ (E, R, D, Q)"""


class _DLATCH_NN1_(_DLATCH3_):
    """module _DLATCH_NN1_ (E, R, D, Q)"""


class _DLATCH_NP0_(_DLATCH3_):
    """module _DLATCH_NP0_ (E, R, D, Q)"""


class _DLATCH_NP1_(_DLATCH3_):
    """module _DLATCH_NP1_ (E, R, D, Q)"""


class _DLATCH_PN0_(_DLATCH3_):
    """module _DLATCH_PN0_ (E, R, D, Q)"""


class _DLATCH_PN1_(_DLATCH3_):
    """module _DLATCH_PN1_ (E, R, D, Q)"""


class _DLATCH_PP0_(_DLATCH3_):
    """module _DLATCH_PP0_ (E, R, D, Q)"""


class _DLATCH_PP1_(_DLATCH3_):
    """module _DLATCH_PP1_ (E, R, D, Q)"""


class _DLATCHSR_(ClassNameParameterComponent):
    """D-type latch with set and reset"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self._enable_level = self.name_to_level(0)
        self._set_level = self.name_to_level(1)
        self._reset_level = self.name_to_level(2)
        self.add_port(PortIn(self, "E"))
        self.add_port(PortIn(self, "S"))
        self.add_port(PortIn(self, "R"))
        self.add_port(PortIn(self, "D"))
        self.add_port(PortOutDelta(self, "Q"))

    def default_state(self):
        self.Q.value = 0

    def update(self):
        if self.R.value == self._reset_level:
            self.Q.value = 0
        elif self.S.value == self._set_level:
            self.Q.value = 1
        elif self.E.value == self._enable_level:
            self.Q.value = self.D.value


class _DLATCHSR_NNN_(_DLATCHSR_):
    """module _DLATCHSR_NNN_ (E, S, R, D, Q)"""


class _DLATCHSR_NNP_(_DLATCHSR_):
    """module _DLATCHSR_NNP_ (E, S, R, D, Q)"""


class _DLATCHSR_NPN_(_DLATCHSR_):
    """module _DLATCHSR_NPN_ (E, S, R, D, Q)"""


class _DLATCHSR_NPP_(_DLATCHSR_):
    """module _DLATCHSR_NPP_ (E, S, R, D, Q)"""


class _DLATCHSR_PNN_(_DLATCHSR_):
    """module _DLATCHSR_PNN_ (E, S, R, D, Q)"""


class _DLATCHSR_PNP_(_DLATCHSR_):
    """module _DLATCHSR_PNP_ (E, S, R, D, Q)"""


class _DLATCHSR_PPN_(_DLATCHSR_):
    """module _DLATCHSR_PPN_ (E, S, R, D, Q)"""


class _DLATCHSR_PPP_(_DLATCHSR_):
    """module _DLATCHSR_PPP_ (E, S, R, D, Q)"""


class _StaticLevel_(Component):
    """Yosys component for static logic levels"""

    def __init__(self, circuit, name):
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "L"))
        self.add_port(PortOutDelta(self, "H"))

    def default_state(self):
        self.L.value = 0
        self.H.value = 1
