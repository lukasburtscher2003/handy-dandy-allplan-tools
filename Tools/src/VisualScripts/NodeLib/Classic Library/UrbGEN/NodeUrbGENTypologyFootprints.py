"""Create independent UrbGEN-like typology outlines for native Allplan VS modelling.

Shapes are parametric interpretations of the documented UrbGEN codes, not copied
from the closed .gha implementation. 7 Courtyard: use the returned outer and
inner polygons with a native boolean subtract; Outlines only contain the outer.
"""
import math
import NemAll_Python_Geometry as Geo
from NodeUtil import NodeBase
NodeBase.trace_node_name('NodeUrbGENTypologyFootprints')
def create_node(init_data): return NodeUrbGENTypologyFootprints(init_data)

def typology_outline(code, length, width, arm_ratio=1.3):
    """Return (outer points, optional courtyard hole); local XY coordinates.

    Typology codes follow UrbGEN (0 I,1 L,2 T,3 H,4 C,5 Plus,7 courtyard).
    This is an approximated parametric geometry, not the original closed-source solver.
    """
    le, wi = float(length), float(width)
    if le <= 0 or wi <= 0: raise ValueError('Length and Width must be > 0')
    if not 0.3 <= arm_ratio <= 8: raise ValueError('ArmLengthRatio must be 0.3..8')
    # Bar thickness varies with arm length ratio and is kept positive.
    d = min(le, wi) / (1.3 + arm_ratio)
    d = max(10.0, min(d, 0.44 * min(le, wi)))
    x1, x2 = d, le-d
    y1, y2 = d, wi-d
    cx1, cx2 = le/2-d/2, le/2+d/2
    cy1, cy2 = wi/2-d/2, wi/2+d/2
    if code == 0:
        return [(0,0),(le,0),(le,wi),(0,wi)], []
    if code == 1:
        return [(0,0),(le,0),(le,d),(d,d),(d,wi),(0,wi)], []
    if code == 2:
        return [(cx1,0),(cx2,0),(cx2,y2),(le,y2),(le,wi),(0,wi),(0,y2),(cx1,y2)], []
    if code == 3:
        return [(0,0),(x1,0),(x1,cy1),(x2,cy1),(x2,0),(le,0),
                (le,wi),(x2,wi),(x2,cy2),(x1,cy2),(x1,wi),(0,wi)], []
    if code == 4:
        return [(0,0),(le,0),(le,wi),(x2,wi),(x2,y1),(x1,y1),(x1,wi),(0,wi)], []
    if code == 5:
        return [(cx1,0),(cx2,0),(cx2,cy1),(le,cy1),(le,cy2),(cx2,cy2),
                (cx2,wi),(cx1,wi),(cx1,cy2),(0,cy2),(0,cy1),(cx1,cy1)], []
    if code == 7:
        return [(0,0),(le,0),(le,wi),(0,wi)], [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]
    raise ValueError('Typology code must be 0..5 or 7 (6 means mixed selection)')


def rotate_translate(poly, x, y, angle):
    rad=math.radians(float(angle)); co,si=math.cos(rad),math.sin(rad)
    return [(x+a*co-b*si, y+a*si+b*co) for a,b in poly]


def footprint_parts(code,x,y,le,wi,angle,arm_ratio):
    outer,hole=typology_outline(code,le,wi,arm_ratio)
    return rotate_translate(outer,x,y,angle), rotate_translate(hole,x,y,angle) if hole else []

def polygon3d(coords,z):
    p=Geo.Polygon3D()
    for x,y in coords:p += Geo.Point3D(float(x),float(y),float(z))
    p += Geo.Point3D(float(coords[0][0]),float(coords[0][1]),float(z))
    return p

def expanded(val,n,key):
    if not isinstance(val,(list,tuple)): val=[val]*n
    if len(val)!=n: raise ValueError(key+' must have '+str(n)+' values')
    return val

class NodeUrbGENTypologyFootprints(NodeBase):
    def _create_output(self):
        p=self.build_ele
        names=('Footprints','ActualAreasM2','TypologyNames','CourtyardIndices',
               'CourtyardOuter','CourtyardInner','IsValid','ErrorMessage')
        for name in names:self._set_init_node_output(getattr(p,name))
        try:
            xs=list(p.X.value); n=len(xs)
            ys=expanded(p.Y.value,n,'Y'); zs=expanded(p.Z.value,n,'Z')
            ls=expanded(p.Lengths.value,n,'Lengths'); ws=expanded(p.Widths.value,n,'Widths')
            angles=expanded(p.AnglesDeg.value,n,'AnglesDeg'); modes=expanded(p.TypologyCodes.value,n,'TypologyCodes')
            arm=float(p.ArmLengthRatio.value)
            polys=[]; areas=[]; titles=[]; ci=[]; co=[]; ch=[]
            labels={0:'I',1:'L',2:'T',3:'H',4:'C',5:'Plus',7:'Courtyard'}
            for i,(x,y,z,le,wi,angle,mode) in enumerate(zip(xs,ys,zs,ls,ws,angles,modes)):
                mode=int(mode)
                outer,inner=footprint_parts(mode,float(x),float(y),float(le),float(wi),float(angle),arm)
                polys.append(polygon3d(outer,z)); titles.append(labels[mode])
                area=abs(shoelace(outer))-abs(shoelace(inner)) if inner else abs(shoelace(outer))
                areas.append(area/1000000.0)
                if inner:
                    ci.append(i);co.append(polygon3d(outer,z));ch.append(polygon3d(inner,z))
            for k,v in dict(Footprints=polys,ActualAreasM2=areas,TypologyNames=titles,
                           CourtyardIndices=ci,CourtyardOuter=co,CourtyardInner=ch,
                           IsValid=True,ErrorMessage='').items():getattr(p,k).value=v
        except Exception as exc:
            p.IsValid.value=False;p.ErrorMessage.value=str(exc);self.error='TypologyFootprints: '+str(exc)

def shoelace(poly):
    if not poly:return 0.0
    return 0.5*sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[i+1 if i+1<len(poly) else 0][0]*poly[i][1] for i in range(len(poly)))
