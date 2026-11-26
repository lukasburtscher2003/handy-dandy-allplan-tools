# -*- coding: utf-8 -*-
"""ModelCHECK – auf Basis von ueberpruefung.py (ScriptObject)."""
from __future__ import annotations

import math
from dataclasses import dataclass

import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_BaseElements as AllplanBaseElements
import NemAll_Python_BasisElements as AllplanBasisElements
from NemAll_Python_IFW_ElementAdapter import BaseElementAdapter, BaseElementAdapterList
from ScriptObjectInteractors.MultiElementSelectInteractor import (
    MultiElementSelectInteractorResult, MultiElementSelectInteractor,
)
from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult
from TypeCollections.ModelEleList import ModelEleList

VOLUME_ID = 226
ATTRIBUTES = {
    "CheckName": (507, "Bezeichnung"),
    "CheckTrade": (209, "Gewerk"),
    "CheckMaterial": (508, "Material"),
    "CheckCostGroup": (5015, "Kostengruppe"),
}
SOLIDS = {"BRep3D", "Polyhedron3D", "Cuboid3D", "Cylinder3D", "Ellipsoid3D",
          "Cone3D", "Sphere3D"}
EPS = 1e-9  # m³: numerical zero, not a minimum meaningful construction volume


def empty(value):
    return value is None or not str(value).strip()


def numeric(value):
    if empty(value) or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def volume_issues(attrs, calculated, geometry_supported, options, tolerance):
    """Pure checking logic. Attribute volume is m³; geometry is converted in adapter."""
    result = []
    raw = attrs.get(VOLUME_ID)
    net = numeric(raw)
    if options["CheckNetVolume"]:
        if empty(raw):
            result.append("Nettovolumen fehlt (@226@)")
        elif net is None:
            result.append("Nettovolumen ungültig (@226@)")
        elif net <= EPS:
            result.append("Nettovolumen null oder negativ")
    if options["CheckGeometry"]:
        if not geometry_supported or calculated is None:
            result.append("Geometrievolumen nicht berechenbar")
        elif calculated <= EPS:
            result.append("Geometrievolumen null oder negativ")
    if options["CheckDeviation"] and net is not None and calculated is not None and net > EPS and calculated > EPS:
        # Keep the original percentage definition, relative to geometry.
        delta = (1 - net / calculated) * 100
        if abs(delta) > tolerance:
            result.append(f"Volumenabweichung {delta:+.2f} %")
    return result


@dataclass
class Finding:
    element: object
    name: str
    reasons: list[str]
    net: float | None
    geometry: float | None


def check_allplan_version(_build_ele: BuildingElement, version: float) -> bool:
    return float(version) >= 2027


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return ModelCheckScriptObject(build_ele, script_object_data)


class ModelCheckScriptObject(BaseScriptObject):
    def __init__(self, build_ele, script_object_data):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        self.selection_result = MultiElementSelectInteractorResult()
        self.selected = []
        self.findings = []
        self.index = -1
        self.completed = False

    def _set(self, name, value):
        getattr(self.build_ele, name).value = value

    def _get(self, name):
        return getattr(self.build_ele, name).value

    def _start_selection(self):
        self.selection_result = MultiElementSelectInteractorResult()
        self.script_object_interactor = MultiElementSelectInteractor(
            self.selection_result, prompt_msg="Zu prüfende Bauteile auswählen ..."
        )

    def start_input(self):
        self._set("Status", "Bauteile auswählen.")
        self._start_selection()
        return super().start_input()

    def start_next_input(self):
        self.selected = list(self.selection_result.sel_elements)
        self.completed = True
        self.script_object_interactor = None
        self._scan()
        return super().start_next_input()

    @staticmethod
    def get_geometry_volume(geometry):
        if geometry is None:
            return None
        try:
            result = AllplanGeo.CalcMass(geometry)
            if result[0] != AllplanGeo.eGeometryErrorCode.eOK:
                return None
            value = float(result[1]) / 1e9  # mm³ -> m³
            return value if math.isfinite(value) else None
        except Exception:
            return None

    def _scan(self):
        self.findings = []
        self.index = -1
        skipped = 0
        options = {key: bool(self._get(key)) for key in
                   ("CheckNetVolume", "CheckGeometry", "CheckDeviation", *ATTRIBUTES)}
        volume_enabled = any(options[key] for key in
                             ("CheckNetVolume", "CheckGeometry", "CheckDeviation"))
        tolerance = max(0.0, float(self._get("Tolerance")))

        for elem in self.selected:
            try:
                attrs = dict(AllplanBaseElements.ElementsAttributeService.GetAttributes(elem))
            except Exception as exc:
                self.findings.append(Finding(elem, "Unbekannt", [f"Attribute nicht lesbar: {exc}"], None, None))
                continue

            reasons = []
            geom = None
            calculated = None
            if volume_enabled:
                try:
                    geom = BaseElementAdapter.GetModelGeometry(elem)
                except Exception:
                    pass
                solid = type(geom).__name__ in SOLIDS
                # Pure 2D objects are normally irrelevant to a volume check.
                candidate = solid or VOLUME_ID in attrs or not self._get("OnlyVolumeCandidates")
                if candidate:
                    calculated = self.get_geometry_volume(geom)
                    reasons.extend(volume_issues(attrs, calculated, geom is not None,
                                                 options, tolerance))
                else:
                    skipped += 1
            for option, (attr_id, label) in ATTRIBUTES.items():
                if options[option] and empty(attrs.get(attr_id)):
                    reasons.append(f"{label} fehlt (@{attr_id}@)")

            if reasons:
                name = str(attrs.get(507) or "(ohne Bezeichnung)")
                self.findings.append(Finding(elem, name, reasons,
                                             numeric(attrs.get(VOLUME_ID)), calculated))

        self._set("SelectedCount", len(self.selected))
        self._set("ErrorCount", len(self.findings))
        self._set("SkippedCount", skipped)
        self._set("Status", "Prüfung abgeschlossen." if any(options.values()) else "Keine Prüfungen aktiviert.")
        if self.findings:
            self.index = 0
        self._show_current()

    def _show_current(self):
        if not 0 <= self.index < len(self.findings):
            self._set("ErrorIndex", "0 / 0")
            self._set("ElementName", "-")
            self._set("ErrorDetail", "Keine Fehler gefunden." if self.completed and self.selected else "-")
            self._set("NetVolume", "-")
            self._set("GeometryVolume", "-")
            return
        finding = self.findings[self.index]
        self._set("ErrorIndex", f"{self.index + 1} / {len(self.findings)}")
        self._set("ElementName", finding.name)
        self._set("ErrorDetail", " | ".join(finding.reasons))
        for param, value in (("NetVolume", finding.net), ("GeometryVolume", finding.geometry)):
            self._set(param, f"{value:.6f}" if value is not None else "-")

    def _zoom(self):
        if not 0 <= self.index < len(self.findings):
            return
        try:
            AllplanBaseElements.ZoomService().ZoomToElement(
                self.findings[self.index].element,
                self.coord_input.GetViewWorldProjection(), 100.0, True)
        except Exception as exc:
            self._set("Status", f"Zoom nicht möglich: {exc}")

    def execute(self) -> CreateElementResult:
        # Preview only: no permanent marker solids or changed attributes.
        markers = ModelEleList()
        if self._get("MarkElements") and 0 <= self.index < len(self.findings):
            try:
                adapters = BaseElementAdapterList()
                adapters.append(self.findings[self.index].element)
                box = AllplanBaseElements.GetMinMaxBox(adapters, 0.0, True)
                start, end = box.GetMin(), box.GetMax()
                pad = 50.0
                p1 = AllplanGeo.Point3D(start.X-pad, start.Y-pad, start.Z-pad)
                p2 = AllplanGeo.Point3D(end.X+pad, end.Y+pad, end.Z+pad)
                # Wireframe bounding box avoids obscuring the selected component.
                corners = [AllplanGeo.Point3D(x,y,z) for x in (p1.X,p2.X)
                           for y in (p1.Y,p2.Y) for z in (p1.Z,p2.Z)]
                common = AllplanBaseElements.CommonProperties()
                common.GetGlobalProperties()
                common.Color = 6
                common.ColorByLayer = False
                for i in range(8):
                    for bit in (1,2,4):
                        j = i ^ bit
                        if i < j:
                            markers.append(AllplanBasisElements.ModelElement3D(
                                common, AllplanGeo.Line3D(corners[i], corners[j])))
            except Exception as exc:
                print(f"[ModelCHECK] Markierung nicht möglich: {exc}")
        return CreateElementResult(preview_elements=markers, placement_point=AllplanGeo.Point3D(),
                                   multi_placement=False, as_static_preview=True)

    def modify_element_property(self, name, value):
        editable = {"CheckNetVolume", "CheckGeometry", "CheckDeviation", "OnlyVolumeCandidates",
                    "Tolerance", "MarkElements", *ATTRIBUTES}
        if name not in editable:
            return False
        self._set(name, value)
        if self.completed and name != "MarkElements":
            self._scan()
        return True

    def on_control_event(self, event_id):
        if event_id == 1000:
            self.selected = []
            self.findings = []
            self.index = -1
            self.completed = False
            self._set("SelectedCount", 0)
            self._set("ErrorCount", 0)
            self._set("SkippedCount", 0)
            self._set("Status", "Bauteile auswählen.")
            self._show_current()
            self._start_selection()
            self.script_object_interactor.start_input(self.coord_input)
            return True
        if event_id == 1001:
            self._scan()
            return True
        if event_id in (1002, 1003) and self.findings:
            self.index = (self.index + (-1 if event_id == 1002 else 1)) % len(self.findings)
            self._show_current()
            self._zoom()
            return True
        if event_id == 1004:
            self._zoom()
            return True
        return super().on_control_event(event_id)

    def on_cancel_function(self):
        self.script_object_interactor = None
        return super().on_cancel_function()
