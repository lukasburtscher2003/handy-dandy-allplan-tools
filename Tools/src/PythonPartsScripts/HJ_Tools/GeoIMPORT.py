"""ALLPLAN 2027: place the completed geodata export in its own coordinate system."""
import hashlib
from pathlib import Path
import shutil
import NemAll_Python_Geometry as Geo
import NemAll_Python_BasisElements as Basis
from NemAll_Python_AllplanSettings import AllplanPaths, AllplanGlobalSettings
from CreateElementResult import CreateElementResult
from TypeCollections.ModelEleList import ModelEleList
from HJ_Tools.GeoImportBundle import load_bundle
from HJ_Tools.GeoWebService import GeoWebService
from HJ_Tools.GeoWebWindow import show_map


def check_allplan_version(_build_ele, version):
    return float(version) >= 2027.0


def _status(build_ele, message):
    if build_ele.ImportStatus.value != message:
        build_ele.ImportStatus.value = message
        print("[GeoIMPORT] " + message)


def _summary(data):
    x, y = data["offset"]
    return (f'{data["count"]} Grundstücke, {len(data["labels"])} Nummern, '
            f'{len(data["terrain"])} Geländepunkte, Luftbild: {"ja" if data["image"] else "nein"}. '
            f'GK-Offset X={x:.3f}, Y={y:.3f} m ({data["mode"]}).')


def _bitmap(image, bounds):
    # Keep the raster with the Allplan project, not in the expiring export cache.
    project = Path(AllplanPaths.GetCurPrjDesignPath())
    if not project.is_dir():
        raise ValueError("Allplan-Projektordner für Bilddateien fehlt.")
    with image.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()[:24]
    target = project / f"GeoIMPORT_{digest}.png"
    if not target.exists():
        shutil.copyfile(image, target)
    x0, y0, x1, y1 = bounds
    polygon = Geo.Polygon2D()
    for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)):
        polygon += Geo.Point2D(x,y)
    props = Basis.BitmapAreaProperties()
    props.BitmapName = str(target)
    props.UseRepeatTile = False
    props.UseMetricalValues = False
    props.UseReferencePoint = False
    props.UseDirectionToReferenceLine = False
    props.XScalingFactor = 1.0
    props.YScalingFactor = 1.0
    props.XOffset = props.YOffset = 0.0
    props.UsePixelMask = False
    common = AllplanGlobalSettings.GetCurrentCommonProperties()
    common.DrawOrder = -10
    return Basis.BitmapAreaElement(common, props, polygon)


def on_control_event(build_ele, event_id):
    try:
        if event_id == 1001:
            with GeoWebService() as service:
                job = show_map(service.url, AllplanPaths.GetPrgPath())
                if job:
                    path = service.import_file(job)
                    data = load_bundle(path, build_ele.SelectedOnly.value)
                    build_ele.ExportFile.value = str(path)
                    _status(build_ele, _summary(data))
        elif event_id == 1004:
            from HJ_Tools.GeoWebService import dependency_report
            _status(build_ele, dependency_report())
        elif event_id == 1003:
            data = load_bundle(
                build_ele.ExportFile.value, build_ele.SelectedOnly.value
            )
            _status(build_ele, _summary(data))
    except Exception as exc:
        _status(build_ele, str(exc))
    return True


def create_element(build_ele, _doc):
    if not build_ele.ExportFile.value:
        return CreateElementResult()
    try:
        data = load_bundle(
            build_ele.ExportFile.value, build_ele.SelectedOnly.value
        )
        elements = ModelEleList()
        if data["image"]:
            elements.append(_bitmap(*data["image"]))
        common = AllplanGlobalSettings.GetCurrentCommonProperties()
        common.DrawOrder = 0
        for ring in data["rings"]:
            polyline = Geo.Polyline2D()
            for x, y in ring:
                polyline += Geo.Point2D(x, y)
            elements.append_geometry_2d(polyline, common)
        for number, x, y, height in data["labels"]:
            props = Basis.TextProperties()
            props.Init()
            props.Height = build_ele.LabelHeight.value
            props.Width = build_ele.LabelHeight.value * 0.75
            props.IsScaleDependent = False
            props.Alignment = Basis.TextAlignment.eMiddleMiddle
            elements.append(Basis.TextElement(common, props, number, Geo.Point2D(x,y)))
        if data["terrain"]:
            symbol = Basis.Symbol3DProperties()
            symbol.IsDigitalTerrainModelSymbol = True
            symbol.SymbolID = 1
            symbol.Height = 2.5
            symbol.Width = 2.5
            for x,y,z in data["terrain"]:
                elements.append(Basis.Symbol3DElement(common, symbol, Geo.Point3D(x,y,z)))

        project_offset = AllplanGlobalSettings.GetOffsetPoint()

        offset_x, offset_y = data["offset"]

        placement = Geo.Point3D(
            offset_x * 1000 - project_offset.X,
            offset_y * 1000 - project_offset.Y,
            -project_offset.Z
        )
        
        
        _status(build_ele, _summary(data))
        return CreateElementResult(
            elements=elements,
            multi_placement=False,
            placement_point=placement,
        )
    except Exception as exc:
        _status(build_ele, f"Import nicht möglich: {exc}")        
        return CreateElementResult()
