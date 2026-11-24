""" implementation of the stub for the building element of the PythonPart NodeDrawingFileSelectionBuildingElement """

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

class NodeDrawingFileSelectionBuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodeDrawingFileSelectionBuildingElement """

    SelectButton: ParameterPropertyTyping[int]
    """ Teilbild auswählen """
    SelectionHint: ParameterPropertyTyping[str]
    """ Teilbild: """
    FileNumber: ParameterPropertyTyping[int]
    """ Teilbildnummer """
    FileNumbers: ParameterPropertyTyping[Any]
    """ Teilbildnummern (Liste) """
    HasSelection: ParameterPropertyTyping[bool]
    """ Teilbild ausgewählt """
    Executed: ParameterPropertyTyping[bool]
    """ Teilbild ausgewählt """
