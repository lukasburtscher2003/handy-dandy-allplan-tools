"""Read projected parcel exports without GIS dependencies."""
import json
import math
from pathlib import Path
from zipfile import ZipFile

MAX_BYTES = 32 * 1024 * 1024
MAX_POINTS = 300_000
LOCAL_CRS = "LOCAL:FRAME_ORIGIN_METRES"


def _read(path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            matches = [
                entry for entry in archive.infolist()
                if entry.filename == "grundstuecke.geojson"
            ]
            if len(matches) != 1:
                raise ValueError("ZIP muss genau eine grundstuecke.geojson enthalten.")
            if matches[0].file_size > MAX_BYTES:
                raise ValueError("Grundstücksdatei ist zu groß.")
            with archive.open(matches[0]) as stream:
                raw = stream.read(MAX_BYTES + 1)
    elif path.suffix.lower() == ".geojson":
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    else:
        raise ValueError("Bitte eine GeoJSON- oder Export-ZIP-Datei auswählen.")
    if len(raw) > MAX_BYTES:
        raise ValueError("Grundstücksdatei ist zu groß.")
    return json.loads(raw.decode("utf-8-sig"))


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Ungültige Koordinate.")
    return float(value)


def parse_parcels(data, selected_only=False):
    """Return (offset in m, closed XY rings in mm, parcel count).

    Preserve the exporter's local origin; never interpret degrees as metres.
    """
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("Keine GeoJSON-FeatureCollection.")
    crs = data.get("crs") or {}
    if crs.get("properties", {}).get("name") != LOCAL_CRS:
        raise ValueError("Im Geodatenexport einen lokalen Ursprung und GeoJSON wählen.")
    offset = data.get("coordinateOffset")
    if not isinstance(offset, list) or len(offset) < 2:
        raise ValueError("Koordinatenoffset fehlt.")
    offset = tuple(_number(v) for v in offset[:2])
    rings = []
    count = total = 0
    for feature in data["features"]:
        props = feature.get("properties") or {}
        if selected_only and props.get("selection") != "selected":
            continue
        geometry = feature["geometry"]
        kind = geometry["type"]
        if kind == "Polygon":
            polygons = [geometry["coordinates"]]
        elif kind == "MultiPolygon":
            polygons = geometry["coordinates"]
        else:
            raise ValueError("Nicht unterstützte Grundstücksgeometrie: " + kind)
        for polygon in polygons:
            for ring in polygon:
                points = [(_number(p[0]) * 1000, _number(p[1]) * 1000) for p in ring]
                # Remove only consecutive duplicates, retain interior boundaries.
                points = [p for i, p in enumerate(points) if i == 0 or p != points[i-1]]
                if points and points[0] != points[-1]:
                    points.append(points[0])
                if len(set(points)) < 3:
                    raise ValueError("Grundstücksgrenze hat weniger als drei Eckpunkte.")
                total += len(points)
                if total > MAX_POINTS:
                    raise ValueError("Zu viele Eckpunkte. Kleineren Bereich exportieren.")
                rings.append(points)
        count += 1
    if not rings:
        raise ValueError("Keine Grundstücksgrenzen in dieser Auswahl.")
    return offset, rings, count


def load_parcels(path, selected_only=False):
    return parse_parcels(_read(path), selected_only)
