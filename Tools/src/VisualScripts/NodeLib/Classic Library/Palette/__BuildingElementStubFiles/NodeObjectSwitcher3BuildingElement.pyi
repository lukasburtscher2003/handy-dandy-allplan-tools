""" implementation of the stub for the building element of the PythonPart NodeObjectSwitcher3BuildingElement """

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

class NodeObjectSwitcher3BuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodeObjectSwitcher3BuildingElement """

    ListSelector: ParameterPropertyTyping[int]
    """ Selector """
    RadioButton1: ParameterPropertyTyping[(str | int | float)]
    """ Objects Group 1 """
    RadioButton2: ParameterPropertyTyping[(str | int | float)]
    """ Objects Group 2 """
    RadioButton3: ParameterPropertyTyping[(str | int | float)]
    """ Objects Group 3 """
    Objects1: ParameterPropertyTyping[Any]
    """ Objects1 """
    Objects2: ParameterPropertyTyping[Any]
    """ Objects2 """
    Objects3: ParameterPropertyTyping[Any]
    """ Objects3 """
    Objects: ParameterPropertyTyping[Any]
    """ Objects """
    CreateModelObjects: ParameterPropertyTyping[bool]
    """ Objects """
    CreateModelPreviewObjects: ParameterPropertyTyping[bool]
    """ Objects """
    Executed: ParameterPropertyTyping[bool]
    """ Objects """
