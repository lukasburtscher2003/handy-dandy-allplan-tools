"""UrbGEN – pairwise collision areas for horizontal building footprints.

ObjectsA/B are parallel lists from UrbGEN_Pairwise.
Units: geometry in mm -> CollisionAreas in m².
No overlap => exactly 0.0 and False for that pair.
Invalid geometry => ValidResults False (never silently treat a failed operation as clear).
"""
import math
import NemAll_Python_Geometry as Geo
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENCollisionCheck')


def create_node(init_data):
    return NodeUrbGENCollisionCheck(init_data)


def _is_valid(obj):
    if obj is None:
        return False
    if hasattr(obj, 'IsValid'):
        return bool(obj.IsValid())
    return True


def _polygon2d(obj):
    """Project 2D/3D footprint to XY; input must be a horizontal polygon."""
    if isinstance(obj, Geo.Polygon2D):
        return obj
    if isinstance(obj, Geo.Polygon3D):
        result = Geo.ConvertTo2D(obj)
        # The generic overload returns a polygon object, not a tuple.
        if isinstance(result, tuple):
            if len(result) == 2 and isinstance(result[0], bool):
                return result[1] if result[0] else None
        return result
    raise TypeError('Expected Polygon2D or horizontal Polygon3D; got ' + type(obj).__name__)


def collision_area_m2(obj_a, obj_b):
    """Return non-negative area in m². Raises on unsupported/broken geometry."""
    a, b = _polygon2d(obj_a), _polygon2d(obj_b)
    if not _is_valid(a) or not _is_valid(b):
        raise ValueError('Invalid footprint polygon')
    err, section, _union, _subtract_a, _subtract_b = Geo.MakeBoolean(a, b)
    # A valid no-overlap calculation may yield an invalid/empty section.
    if err != Geo.eGeometryErrorCode.eOK:
        raise ValueError('MakeBoolean failed: ' + str(err))
    if not _is_valid(section):
        return 0.0
    area_result = Geo.CalcArea(section)
    area_mm2 = float(area_result[0] if isinstance(area_result, tuple) else area_result)
    if not math.isfinite(area_mm2):
        raise ValueError('Non-finite intersection area')
    return max(0.0, abs(area_mm2)) / 1_000_000.0


def check_pairs(objects_a, objects_b, tolerance_m2=0.001):
    """Return areas, booleans, valid flags, per-pair message strings."""
    if not isinstance(objects_a, (list, tuple)) or not isinstance(objects_b, (list, tuple)):
        raise TypeError('ObjectsA and ObjectsB must be lists')
    if len(objects_a) != len(objects_b):
        raise ValueError('ObjectsA and ObjectsB must have equal lengths')
    tol = float(tolerance_m2)
    if not math.isfinite(tol) or tol < 0:
        raise ValueError('Tolerance must be a non-negative finite m² value')
    areas, states, valid, messages = [], [], [], []
    for pair_index, (a, b) in enumerate(zip(objects_a, objects_b)):
        try:
            area = collision_area_m2(a, b)
            areas.append(area)
            states.append(area > tol)
            valid.append(True)
            messages.append('')
        except Exception as exc:
            areas.append(0.0)   # placeholder only; NOT a verified no-collision result
            states.append(False)
            valid.append(False)
            messages.append('Pair %d: %s' % (pair_index, exc))
    return areas, states, valid, messages


class NodeUrbGENCollisionCheck(NodeBase):
    def _create_output(self):
        el = self.build_ele
        for prop in (el.CollisionAreas, el.CollisionStates, el.ValidResults, el.ErrorMessages):
            self._set_init_node_output(prop)
        try:
            result = check_pairs(el.ObjectsA.value, el.ObjectsB.value, el.Tolerance.value)
            el.CollisionAreas.value = result[0]
            el.CollisionStates.value = result[1]
            el.ValidResults.value = result[2]
            el.ErrorMessages.value = result[3]
            if not all(result[2]):
                self.warning = 'UrbGEN CollisionCheck: %d pair(s) could not be evaluated' % result[2].count(False)
        except Exception as exc:
            self.error = 'UrbGEN CollisionCheck: ' + str(exc)
