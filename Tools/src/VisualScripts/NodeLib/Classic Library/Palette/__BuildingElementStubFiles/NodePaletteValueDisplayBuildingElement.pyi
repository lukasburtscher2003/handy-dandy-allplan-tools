""" implementation of the stub for the building element of the PythonPart NodePaletteValueDisplayBuildingElement """

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

class NodePaletteValueDisplayBuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodePaletteValueDisplayBuildingElement """

    InputString: ParameterPropertyTyping[str]
    """ Text """
    InputInteger: ParameterPropertyTyping[int]
    """ Ganzzahl """
    InputDouble: ParameterPropertyTyping[float]
    """ Zahl """
    InputBoolean: ParameterPropertyTyping[bool]
    """ Ja/Nein """
    InputLength: ParameterPropertyTyping[float]
    """ Laenge [mm] """
    InputArea: ParameterPropertyTyping[float]
    """ Flaeche [mm2] """
    InputVolume: ParameterPropertyTyping[float]
    """ Volumen [mm3] """
    InputAngle: ParameterPropertyTyping[float]
    """ Winkel [Grad] """
    DataType: ParameterPropertyTyping[str]
    """ Quelle: String/Integer/Double/Boolean/Length/Area/Volume/Angle/Auto """
    Unit: ParameterPropertyTyping[str]
    """ Ausgabeeinheit: Auto/mm/cm/m/mm2/cm2/m2/mm3/cm3/m3/Grad/% """
    DisplayedText: ParameterPropertyTyping[str]
    """ Anzeige """
    Executed: ParameterPropertyTyping[bool]
    """ Anzeige """
