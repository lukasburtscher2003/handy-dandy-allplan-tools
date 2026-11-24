""" implementation of the stub for the building element of the PythonPart NodeUrbGENEditBuildingBuildingElement """

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

class NodeUrbGENEditBuildingBuildingElement(BuildingElement):
    """ implementation of the stub for the building element of the PythonPart NodeUrbGENEditBuildingBuildingElement """

    Boundary: ParameterPropertyTyping[AllplanGeo.Polygon3D]
    """ Boundary """
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
    Floors: ParameterPropertyTyping[Any]
    """ Floors """
    TypologyCodes: ParameterPropertyTyping[Any]
    """ TypologyCodes """
    BuildingIndex: ParameterPropertyTyping[int]
    """ BuildingIndex """
    VariantIndex: ParameterPropertyTyping[int]
    """ VariantIndex """
    MinDistance: ParameterPropertyTyping[float]
    """ MinDistance """
    ArmLengthRatio: ParameterPropertyTyping[float]
    """ ArmLengthRatio """
    BuildingCountDisplay: ParameterPropertyTyping[str]
    """ Gebäudeanzahl """
    EditX: ParameterPropertyTyping[float]
    """ EditX """
    EditY: ParameterPropertyTyping[float]
    """ EditY """
    EditLength: ParameterPropertyTyping[float]
    """ EditLength """
    EditWidth: ParameterPropertyTyping[float]
    """ EditWidth """
    EditAngleDeg: ParameterPropertyTyping[float]
    """ EditAngleDeg """
    EditFloors: ParameterPropertyTyping[int]
    """ EditFloors """
    FloorHeight: ParameterPropertyTyping[float]
    """ Geschosshöhe """
    EditHeight: ParameterPropertyTyping[float]
    """ Gebäudehöhe """
    InfoPictureSnapping: ParameterPropertyTyping[str]
    """ Wenn der Haken gesetzt ist, kann die Gebäudehöhe nur in Geschoss-Schritten verändert werden. """
    HeightMode: ParameterPropertyTyping[bool]
    """ Geschoss-Snapping """
    EditTypologyCode: ParameterPropertyTyping[int]
    """ Gebäudeform """
    EditTypologyOption0: ParameterPropertyTyping[(str | int | float)]
    """ I – Rechteck """
    EditTypologyOption1: ParameterPropertyTyping[(str | int | float)]
    """ L – Form """
    EditTypologyOption2: ParameterPropertyTyping[(str | int | float)]
    """ T – Form """
    EditTypologyOption3: ParameterPropertyTyping[(str | int | float)]
    """ H – Form """
    EditTypologyOption4: ParameterPropertyTyping[(str | int | float)]
    """ C / U – Form """
    EditTypologyOption5: ParameterPropertyTyping[(str | int | float)]
    """ Kreuz / Plus """
    EditTypologyOption7: ParameterPropertyTyping[(str | int | float)]
    """ Innenhof """
    ShowBuildingHandles: ParameterPropertyTyping[bool]
    """ Gebäudegriffe anzeigen """
    DeleteBuildingButton: ParameterPropertyTyping[int]
    """ Ausgewähltes Gebäude löschen """
    ResetVariantButton: ParameterPropertyTyping[int]
    """ Variante zurücksetzen """
    InfoPicture: ParameterPropertyTyping[str]
    """ Wenn aktiviert, bleiben Änderungen an Position, Länge, Breite, Winkel, Geschossen und Typologie trotz Grenz- oder Abstandskonflikten erhalten """
    AllowConflictingTypology: ParameterPropertyTyping[bool]
    """ Alle Geometriekonflikte ignorieren """
    OutX: ParameterPropertyTyping[Any]
    """ OutX """
    OutY: ParameterPropertyTyping[Any]
    """ OutY """
    OutZ: ParameterPropertyTyping[Any]
    """ OutZ """
    OutLengths: ParameterPropertyTyping[Any]
    """ OutLengths """
    OutWidths: ParameterPropertyTyping[Any]
    """ OutWidths """
    OutAnglesDeg: ParameterPropertyTyping[Any]
    """ OutAnglesDeg """
    OutFloors: ParameterPropertyTyping[Any]
    """ OutFloors """
    OutTypologyCodes: ParameterPropertyTyping[Any]
    """ OutTypologyCodes """
    EditAccepted: ParameterPropertyTyping[bool]
    """ EditAccepted """
    IsValid: ParameterPropertyTyping[bool]
    """ IsValid """
    ErrorMessage: ParameterPropertyTyping[str]
    """ ErrorMessage """
    SelectedBuildingIndex: ParameterPropertyTyping[int]
    """ SelectedBuildingIndex """
    SelectedVariantIndex: ParameterPropertyTyping[int]
    """ SelectedVariantIndex """
    OutHeights: ParameterPropertyTyping[Any]
    """ Gebäudehöhen für Extrusion """
    Handles: ParameterPropertyTyping[Any]
    """ Handles """
    BuildingCount: ParameterPropertyTyping[int]
    """ Gebäudeanzahl aktuelle Variante """
    SelectedSourceIndex: ParameterPropertyTyping[int]
    """ Originalindex des ausgewählten Gebäudes """
    GeometryValid: ParameterPropertyTyping[bool]
    """ Geometrie erfüllt Baugrenze/Mindestabstand """
    CreateModelObjects: ParameterPropertyTyping[bool]
    """ Geometrie erfüllt Baugrenze/Mindestabstand """
    CreateModelPreviewObjects: ParameterPropertyTyping[bool]
    """ Geometrie erfüllt Baugrenze/Mindestabstand """
    Executed: ParameterPropertyTyping[bool]
    """ Geometrie erfüllt Baugrenze/Mindestabstand """
    EditOverrides: ParameterPropertyTyping[str]
    """ EditOverrides """
    LoadedKey: ParameterPropertyTyping[str]
    """ LoadedKey """
    LoadedValues: ParameterPropertyTyping[list[str]]
    """ LoadedValues """
    CreateHandles: ParameterPropertyTyping[bool]
    """ CreateHandles """
    HeightOverrides: ParameterPropertyTyping[str]
    """ Höhenänderungen je Variante """
    LoadedHeight: ParameterPropertyTyping[float]
    """ Geladene Gebäudehöhe """
    DeletedBuildings: ParameterPropertyTyping[str]
    """ Gelöschte Gebäude je Variante """
    DeleteLock: ParameterPropertyTyping[str]
    """ Schutz bei wiederholtem Klick """
