"""UrbGEN BoundaryAlign: rotation angles based on nearest actual boundary segment.

Polygon3D and Point3D coordinates are in Allplan model units (usually mm).
Output ZAnglesDeg are degrees, normalized to [0, 180), for a long-axis
orientation parallel to the nearest segment. Rotate about each placement point.
"""
import math
import NemAll_Python_Geometry as Geo
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENBoundaryAlign')


def create_node(init_data):
    return NodeUrbGENBoundaryAlign(init_data)


def _coords(point):
    return float(point.X), float(point.Y)


def _vertices(boundary):
    if not isinstance(boundary, Geo.Polygon3D):
        raise TypeError('Boundary must be a Polygon3D')
    count = int(boundary.Count())
    points = [_coords(boundary.GetPoint(i)) for i in range(count)]
    if len(points) >= 2 and math.dist(points[0], points[-1]) <= 1e-7:
        points.pop()
    if len(points) < 3:
        raise ValueError('Boundary requires at least 3 distinct vertices')
    if any(not all(map(math.isfinite, p)) for p in points):
        raise ValueError('Boundary contains non-finite coordinates')
    return points


def _nearest_segment(point, vertices):
    px, py = _coords(point)
    if not math.isfinite(px) or not math.isfinite(py):
        raise ValueError('Placement point contains non-finite coordinates')
    closest = None
    for index in range(len(vertices)):
        ax, ay = vertices[index]
        bx, by = vertices[(index + 1) % len(vertices)]
        vx, vy = bx - ax, by - ay
        size2 = vx * vx + vy * vy
        if size2 <= 1e-16:
            continue
        t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / size2))
        dx, dy = px - (ax + t * vx), py - (ay + t * vy)
        distance2 = dx * dx + dy * dy
        if closest is None or distance2 < closest[0]:
            angle = math.degrees(math.atan2(vy, vx)) % 180.0
            closest = (distance2, index, angle)
    if closest is None:
        raise ValueError('All boundary edges have zero length')
    return closest


def alignment_angles(points, vertices, offset_degrees=0.0):
    if not isinstance(points, (list, tuple)):
        raise TypeError('PlacementPoints must be a list')
    offset = float(offset_degrees)
    if not math.isfinite(offset):
        raise ValueError('AngleOffset must be finite')
    angles, indices, distances, valid, errors = [], [], [], [], []
    for i, point in enumerate(points):
        try:
            d2, edge, angle = _nearest_segment(point, vertices)
            angles.append((angle + offset) % 180.0)
            indices.append(edge)
            distances.append(math.sqrt(d2))
            valid.append(True)
            errors.append('')
        except Exception as exc:
            angles.append(0.0)
            indices.append(-1)
            distances.append(-1.0)
            valid.append(False)
            errors.append('Point %d: %s' % (i, exc))
    return angles, indices, distances, valid, errors


class NodeUrbGENBoundaryAlign(NodeBase):
    def _create_output(self):
        el = self.build_ele
        for prop in (el.ZAnglesDeg, el.EdgeIndices, el.EdgeDistances, el.ValidResults, el.ErrorMessages):
            self._set_init_node_output(prop)
        try:
            vertices = _vertices(el.Boundary.value)
            values = alignment_angles(el.PlacementPoints.value, vertices, el.AngleOffset.value)
            for prop, value in zip((el.ZAnglesDeg, el.EdgeIndices, el.EdgeDistances, el.ValidResults, el.ErrorMessages), values):
                prop.value = value
            if not all(values[3]):
                self.warning = 'UrbGEN BoundaryAlign: %d invalid point(s)' % values[3].count(False)
        except Exception as exc:
            self.error = 'UrbGEN BoundaryAlign: ' + str(exc)
