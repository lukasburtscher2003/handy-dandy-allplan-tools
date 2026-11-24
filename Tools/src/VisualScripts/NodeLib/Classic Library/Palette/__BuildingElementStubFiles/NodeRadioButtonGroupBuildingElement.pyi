""" implementation of the stub for the building element of the PythonPart NodeRadioButtonGroupBuildingElement """

# pylint: disable=unused-import

from typing import NamedTuple, Tuple, TypeVar, Union, Generic

from datetime import date

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_ArchElements as AllplanArchEle
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_Palette as AllplanPalette

from AttributeIdValue import AttributeIdValue
from BuildingElement import BuildingElement
from ParameterProperty import ParameterProperty
from ParameterPropertyTyping import ParameterPropertyTyping
from StdReinfShapeBuilder.ReinforcementShapeProperties import ReinforcementShapeProperties

from ValueTypes.Data.ElementConnection import ElementConnection

class NodeRadioButtonGroupBuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodeRadioButtonGroupBuildingElement """

    ShowInOneRow: ParameterPropertyTyping[bool]
    """ Show in one row """
    RadioButtonGroup: ParameterPropertyTyping[int]
    """   """
    Value0: ParameterPropertyTyping[(str | int | float)]
    """ Value 0 """
    Value1: ParameterPropertyTyping[(str | int | float)]
    """ Value 1 """
    Value2: ParameterPropertyTyping[(str | int | float)]
    """ Value 2 """
    Value3: ParameterPropertyTyping[(str | int | float)]
    """ Value 3 """
    Value4: ParameterPropertyTyping[(str | int | float)]
    """ Value 4 """
    Value5: ParameterPropertyTyping[(str | int | float)]
    """ Value 5 """
    IsVisible: ParameterPropertyTyping[(Any | Any)]
    """ Visible state """
    IsEnabled: ParameterPropertyTyping[(Any | Any)]
    """ Enabled state """
    Value: ParameterPropertyTyping[int]
    """ Value """
    Executed: ParameterPropertyTyping[bool]
    """ Value """
