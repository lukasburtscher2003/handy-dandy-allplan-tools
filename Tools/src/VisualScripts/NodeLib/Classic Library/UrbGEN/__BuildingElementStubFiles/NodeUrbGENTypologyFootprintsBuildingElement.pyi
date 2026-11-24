""" implementation of the stub for the building element of the PythonPart NodeUrbGENTypologyFootprintsBuildingElement """

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

class NodeUrbGENTypologyFootprintsBuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodeUrbGENTypologyFootprintsBuildingElement """

    X: ParameterPropertyTyping[Any]
    """ X """
    Y: ParameterPropertyTyping[Any]
    """ Y """
    Z: ParameterPropertyTyping[Any]
    """ Z """
    Lengths: ParameterPropertyTyping[Any]
    """ Lengths """
    Widths: ParameterPropertyTyping[Any]
    """ Widths """
    AnglesDeg: ParameterPropertyTyping[Any]
    """ AnglesDeg """
    TypologyCodes: ParameterPropertyTyping[Any]
    """ TypologyCodes """
    ArmLengthRatio: ParameterPropertyTyping[float]
    """ ArmLengthRatio """
    Footprints: ParameterPropertyTyping[AllplanGeo.list{Polygon3D}]
    """ Footprints """
    ActualAreasM2: ParameterPropertyTyping[Any]
    """ ActualAreasM2 """
    TypologyNames: ParameterPropertyTyping[Any]
    """ TypologyNames """
    CourtyardIndices: ParameterPropertyTyping[Any]
    """ CourtyardIndices """
    CourtyardOuter: ParameterPropertyTyping[AllplanGeo.list{Polygon3D}]
    """ CourtyardOuter """
    CourtyardInner: ParameterPropertyTyping[AllplanGeo.list{Polygon3D}]
    """ CourtyardInner """
    IsValid: ParameterPropertyTyping[bool]
    """ IsValid """
    ErrorMessage: ParameterPropertyTyping[str]
    """ ErrorMessage """
    CreateModelObjects: ParameterPropertyTyping[bool]
    """ ErrorMessage """
    CreateModelPreviewObjects: ParameterPropertyTyping[bool]
    """ ErrorMessage """
    Executed: ParameterPropertyTyping[bool]
    """ ErrorMessage """
