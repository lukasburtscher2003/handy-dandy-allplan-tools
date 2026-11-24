""" implementation of the stub for the building element of the PythonPart NodeUrbGENSetbackSurfacesBuildingElement """

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

class NodeUrbGENSetbackSurfacesBuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodeUrbGENSetbackSurfacesBuildingElement """

    Footprints: ParameterPropertyTyping[AllplanGeo.list{Polygon3D}]
    """ Gebäudegrundrisse """
    Heights: ParameterPropertyTyping[Any]
    """ Gebäudehöhen """
    HeightFactor: ParameterPropertyTyping[float]
    """ Höhenfaktor """
    GroundZ: ParameterPropertyTyping[float]
    """ Grundebene Z """
    SetbackSurfaces: ParameterPropertyTyping[AllplanGeo.list{Polygon3D}]
    """ Abstandsflächen """
    BuildingIndices: ParameterPropertyTyping[Any]
    """ Gebäudeindizes je Fläche """
    SetbackDistances: ParameterPropertyTyping[Any]
    """ Abstand je Gebäude """
    SurfaceCounts: ParameterPropertyTyping[Any]
    """ Flächenzahl je Gebäude """
    IsValid: ParameterPropertyTyping[bool]
    """ Gültig """
    ErrorMessage: ParameterPropertyTyping[str]
    """ Fehlertext """
    CreateModelObjects: ParameterPropertyTyping[bool]
    """ Fehlertext """
    CreateModelPreviewObjects: ParameterPropertyTyping[bool]
    """ Fehlertext """
    Executed: ParameterPropertyTyping[bool]
    """ Fehlertext """
