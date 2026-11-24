"""UrbGEN BoundaryCheck: one area and status per building footprint.

Units: Allplan geometry in mm, resulting areas and tolerance in m².
InsideStates is TRUE only for a successfully evaluated footprint within tolerance.
Unreliable geometry is NEVER silently accepted.
"""
import math
import NemAll_Python_Geometry as Geo
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENBoundaryCheck')


def create_node(init_data):
    return NodeUrbGENBoundaryCheck(init_data)


def _valid(obj):
    if obj is None:
        return False
    return bool(obj.IsValid()) if hasattr(obj, 'IsValid') else True


def _polygon2d(obj):
    if isinstance(obj, Geo.Polygon2D):
        return obj
    if isinstance(obj, Geo.Polygon3D):
        value = Geo.ConvertTo2D(obj)
        if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], bool):
            value = value[1] if value[0] else None
        if not isinstance(value, Geo.Polygon2D):
            raise ValueError('Could not convert Polygon3D to Polygon2D')
        return value
    raise TypeError('Expected Polygon2D or horizontal Polygon3D, got ' + type(obj).__name__)


def _area_m2(polygon):
    if not _valid(polygon):
        return 0.0
    result = Geo.CalcArea(polygon)
    area = float(result[0] if isinstance(result, tuple) else result)
    if not math.isfinite(area):
        raise ValueError('Non-finite area')
    return abs(area) / 1000000.0


def _one_check(footprint, boundary, tolerance):
    footprint = _polygon2d(footprint)
    if not _valid(footprint):
        raise ValueError('Invalid building footprint')
    total_area = _area_m2(footprint)
    if total_area <= 0:
        raise ValueError('Building footprint has zero area')
    err, section, _union, _sub_a, _sub_b = Geo.MakeBoolean(footprint, boundary)
    if err != Geo.eGeometryErrorCode.eOK:
        raise ValueError('MakeBoolean failed: ' + str(err))
    intersect_area = _area_m2(section) if _valid(section) else 0.0
    outside = max(0.0, total_area - intersect_area)
    return outside <= tolerance, outside


def check_footprints(buildings, boundary, tolerance_m2=0.001):
    if not isinstance(buildings, (list, tuple)):
        raise TypeError('BuildingFootprints must be a list')
    tol = float(tolerance_m2)
    if not math.isfinite(tol) or tol < 0:
        raise ValueError('Tolerance must be a non-negative finite area in m²')
    # Native Allplan OffsetPolygon3DByDistance returns list{Polygon3D}.
    # Accept one boundary; do not silently ignore additional independent areas.
    if isinstance(boundary, (list, tuple)):
        if len(boundary) != 1:
            raise ValueError('Boundary must contain exactly one polygon (received %d)' % len(boundary))
        boundary = boundary[0]
    boundary = _polygon2d(boundary)
    if not _valid(boundary) or _area_m2(boundary) <= 0:
        raise ValueError('Invalid or empty buildable boundary polygon')
    states, outside_areas, valid, messages = [], [], [], []
    for i, footprint in enumerate(buildings):
        try:
            inside, outside = _one_check(footprint, boundary, tol)
            states.append(inside)
            outside_areas.append(outside)
            valid.append(True)
            messages.append('')
        except Exception as exc:
            states.append(False)  # fail closed
            outside_areas.append(0.0)  # placeholder ONLY, see ValidResults
            valid.append(False)
            messages.append('Building %d: %s' % (i, exc))
    return states, outside_areas, valid, messages


class NodeUrbGENBoundaryCheck(NodeBase):
    def _create_output(self):
        el = self.build_ele
        for prop in (el.InsideStates, el.OutsideAreas, el.ValidResults, el.ErrorMessages):
            self._set_init_node_output(prop)
        try:
            states, areas, valid, messages = check_footprints(
                el.BuildingFootprints.value, el.Boundary.value, el.Tolerance.value)
            el.InsideStates.value = states
            el.OutsideAreas.value = areas
            el.ValidResults.value = valid
            el.ErrorMessages.value = messages
            if not all(valid):
                self.warning = 'UrbGEN BoundaryCheck: %d invalid footprint(s)' % valid.count(False)
        except Exception as exc:
            self.error = 'UrbGEN BoundaryCheck: ' + str(exc)
