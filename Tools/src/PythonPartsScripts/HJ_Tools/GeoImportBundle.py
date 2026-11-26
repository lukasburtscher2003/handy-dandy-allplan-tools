"""Read the native handoff in the exporter coordinate system (metres -> mm)."""
import json
import math
from pathlib import Path
from HJ_Tools.GeoImportData import parse_parcels, load_parcels

MAX_TERRAIN_POINTS = 100_000


def number(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Ungültige Koordinate.")
    return value


def mm(values):
    return tuple(number(v) * 1000 for v in values)


def read_json(path):
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Importdatei zu groß.")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def terrain_points(path):
    points = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            values = line.split()
            if len(values) != 3:
                raise ValueError("XYZ-Datei: genau drei Koordinaten erwartet.")
            points.append(mm(values))
            if len(points) > MAX_TERRAIN_POINTS:
                raise ValueError("Mehr als 100.000 Geländepunkte. Gröbere Rasterweite wählen.")
    return points


def image_bounds(worldfile, width, height):
    # Worldfile stores centre of the upper-left pixel, not its corner.
    a, d, b, e, c, f = map(number, worldfile.read_text().split())
    if a <= 0 or e >= 0 or b != 0 or d != 0 or width <= 0 or height <= 0:
        raise ValueError("Nur nordorientiertes Luftbild mit positivem Rasterabstand unterstützt.")
    left = c - a / 2
    top = f - e / 2
    return mm((left, top + e * height, left + a * width, top))


def load_bundle(path, selected_only=False):
    path = Path(path)
    if path.name != "metadaten.json":
        offset, rings, count = load_parcels(path, selected_only)
        return dict(offset=offset, rings=rings, count=count, labels=[], terrain=[], image=None, mode="local")
    meta = read_json(path)
    if meta.get("allplanImportVersion") != 1:
        raise ValueError("Bitte einen neuen GeoIMPORT-Export verwenden.")
    opts = meta["options"]
    types = set(opts["types"])
    offset = tuple(number(v) for v in opts["offset"][:2])
    if len(offset) != 2:
        raise ValueError("XY-Offset fehlt.")
    mode = opts["originMode"]
    if mode not in ("world", "frame", "custom") or (mode == "world" and offset != (0, 0)):
        raise ValueError("Ungültiger Koordinatenursprung.")
    data = dict(offset=offset, rings=[], count=0, labels=[], terrain=[], image=None, mode=mode)
    folder = path.parent
    if "parcels" in types:
        parcels = read_json(folder / "allplan_parcels.json")
        chosen = [f for f in parcels["features"] if not selected_only or f["properties"].get("selection") == "selected"]
        if tuple(parcels["coordinateOffset"][:2]) != offset:
            raise ValueError("Grundstücks-Offset stimmt nicht mit Export überein.")
        if chosen:
            _, data["rings"], data["count"] = parse_parcels(parcels, selected_only)
        for feature in read_json(folder / "allplan_labels.json")["features"]:
            props = feature["properties"]
            if selected_only and props.get("selection") != "selected":
                continue
            x, y = mm(feature["geometry"]["coordinates"][:2])
            height = number(props.get("label_height", 1.5)) * 1000
            if height <= 0:
                raise ValueError("Ungültige Texthöhe.")
            data["labels"].append((str(props["gnr"]), x, y, height))
    if "terrain" in types:
        data["terrain"] = terrain_points(folder / "gelaende.xyz")
    if "aerial" in types:
        from PIL import Image
        image = folder / "luftbild.png"
        with Image.open(image) as raster:
            width, height = raster.size
        bounds = image_bounds(folder / "luftbild.pgw", width, height)
        expected = mm(meta["outputBounds"])
        if any(abs(a-b)>1.0 for a,b in zip(bounds, expected)):
            raise ValueError("Luftbildgrenzen stimmen nicht mit Exportkoordinaten überein.")
        data["image"] = (image, bounds)
    if not (data["rings"] or data["labels"] or data["terrain"] or data["image"]):
        raise ValueError("Keine Geodaten für den Import vorhanden.")
    return data
