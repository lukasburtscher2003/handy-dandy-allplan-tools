""" implementation of the stub for the building element of the PythonPart NodeCreateModelObjectInDrawingFileBuildingElement """

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

class NodeCreateModelObjectInDrawingFileBuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodeCreateModelObjectInDrawingFileBuildingElement """

    Apply: ParameterPropertyTyping[str]
    """ Apply """
    Element: ParameterPropertyTyping[Any]
    """ Model element """
    TargetDrawingFile: ParameterPropertyTyping[int]
    """ Ziel-Teilbild (anderes, aktiv im Hintergrund geladenes TB) """
    ObjectToDelete: ParameterPropertyTyping[Any]
    """ Object to delete """
    Executed: ParameterPropertyTyping[bool]
    """ Object to delete """
