"""UrbGEN: separated plan-view setback surfaces for every exterior wall.
Schematic only: distance = building height * factor (default 0.6).
Each wall is an individual horizontal Polygon3D at GroundZ. No merged offset.
"""
import math
import NemAll_Python_Geometry as Geo
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENSetbackSurfaces')

def create_node(init_data):
    return NodeUrbGENSetbackSurfaces(init_data)


def _xy_points(polygon):
    pts=[(float(p.X),float(p.Y)) for p in polygon.Points]
    if len(pts)>1 and math.dist(pts[0],pts[-1])<1e-6:
        pts.pop()
    # ignore duplicate adjacent points
    clean=[]
    for pt in pts:
        if not clean or math.dist(pt,clean[-1])>1e-6:
            clean.append(pt)
    if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-6:
        clean.pop()
    return clean


def _signed_area(points):
    return 0.5*sum(x*y1-x1*y for (x,y),(x1,y1) in zip(points,points[1:]+points[:1]))


def _make_polygon(points,z):
    poly=Geo.Polygon3D()
    for x,y in points:
        poly += Geo.Point3D(float(x),float(y),float(z))
    poly += Geo.Point3D(float(points[0][0]),float(points[0][1]),float(z))
    return poly


def _extend(value,n,field):
    if isinstance(value,(list,tuple)):
        if len(value)==n:return list(value)
        if len(value)==1:return list(value)*n
        raise ValueError(field+' must be scalar, single item or match footprint count')
    return [value]*n


def _wall_surface(a, b, ccw, distance, ground_z):
    """Rectangular horizontal setback strip extending outward from one facade."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    seg = math.hypot(dx, dy)
    if seg < 1e-6 or distance <= 0:
        return None
    ux, uy = dx / seg, dy / seg
    # CCW exterior is to the right of its directed facade segment.
    nx, ny = (uy, -ux) if ccw else (-uy, ux)
    a1 = (a[0] + nx * distance, a[1] + ny * distance)
    b1 = (b[0] + nx * distance, b[1] + ny * distance)
    return _make_polygon([a, b, b1, a1], ground_z)


def calculate_surfaces(footprints, heights, factor=0.6, ground_z=0.0, show_surfaces=True):
    """Pure geometry assembly; returns surfaces, owner indexes, distances, per-building counts."""
    surfaces=[]; owners=[]; ds=[]; counts=[]
    if factor<0 or factor>10: raise ValueError('HeightFactor must be from 0 to 10')
    for i,(footprint,height) in enumerate(zip(footprints,heights)):
        zheight=float(height)
        if not math.isfinite(zheight) or zheight<0: raise ValueError('Height must be non-negative')
        d=zheight*factor
        ds.append(d)
        points=_xy_points(footprint)
        if len(points)<3:raise ValueError('Footprint '+str(i)+' has less than three distinct points')
        area=_signed_area(points)
        if abs(area)<1e-5:raise ValueError('Footprint '+str(i)+' has zero signed area')
        count=0
        for a,b in zip(points,points[1:]+points[:1]):
            if d > 0:
                count += 1
                if show_surfaces:
                    new_surface=_wall_surface(a,b,area>0,d,ground_z)
                    if new_surface is not None:
                        surfaces.append(new_surface); owners.append(i)
        counts.append(count)
    return surfaces,owners,ds,counts


class NodeUrbGENSetbackSurfaces(NodeBase):
    def _create_output(self):
        p=self.build_ele
        for name in ('SetbackSurfaces','BuildingIndices','SetbackDistances','SurfaceCounts','IsValid','ErrorMessage'):
            self._set_init_node_output(getattr(p,name))
        try:
            footprints=list(p.Footprints.value or [])
            heights=_extend(p.Heights.value,len(footprints),'Heights')
            surfaces,owner,distances,counts=calculate_surfaces(
                footprints,heights,float(p.HeightFactor.value),float(p.GroundZ.value),bool(p.ShowSurfaces.value))
            p.SetbackSurfaces.value=surfaces
            p.BuildingIndices.value=owner
            p.SetbackDistances.value=distances
            p.SurfaceCounts.value=counts
            p.IsValid.value=True
            p.ErrorMessage.value=''
        except Exception as exc:
            p.SetbackSurfaces.value=[]
            p.BuildingIndices.value=[]
            p.SetbackDistances.value=[]
            p.SurfaceCounts.value=[]
            p.IsValid.value=False
            p.ErrorMessage.value=str(exc)
            self.error='SetbackSurfaces: '+str(exc)
