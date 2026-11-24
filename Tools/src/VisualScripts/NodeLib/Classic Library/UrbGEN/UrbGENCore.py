"""UrbGEN geometry and Pareto primitives, no Allplan API required."""
import math, random
import NemAll_Python_Geometry as Geo
EPS = 1e-8
# Allplan model units are millimetres: 10 mm = 1 cm.
CM_GRID = 10.0


def cm_round(value):
    """Round a model-coordinate length to the nearest full centimetre."""
    value = float(value)
    return float(math.floor(value / CM_GRID + 0.5) * CM_GRID)


def cm_grid_bounds(low, high):
    """Choose centimetre sizes strictly within the user supplied limits."""
    min_step = math.ceil(float(low) / CM_GRID - 1e-10)
    max_step = math.floor(float(high) / CM_GRID + 1e-10)
    if min_step > max_step:
        raise ValueError('No centimetre increment fits into Min/Max Length or Width bounds')
    return int(min_step), int(max_step)



def vertices_from_boundary(boundary):
    if not isinstance(boundary, Geo.Polygon3D):
        raise TypeError('Boundary needs a single Polygon3D (buildable boundary)')
    pts = [(float(boundary.GetPoint(i).X), float(boundary.GetPoint(i).Y),
            float(boundary.GetPoint(i).Z)) for i in range(int(boundary.Count()))]
    if len(pts) > 1 and math.dist(pts[0][:2],pts[-1][:2]) <= EPS:
        pts.pop()
    if len(pts) < 3:
        raise ValueError('Boundary requires at least three distinct vertices')
    if not all(math.isfinite(v) for pt in pts for v in pt):
        raise ValueError('Non-finite boundary coordinates')
    if max(p[2] for p in pts)-min(p[2] for p in pts)>0.001:
        raise ValueError('Boundary must be horizontal; use a planar polygon')
    coords = [(p[0],p[1]) for p in pts]
    if abs(signed_area(coords))<EPS:
        raise ValueError('Boundary has zero area')
    if any(length2(coords[i],coords[(i+1)%len(coords)])<=EPS for i in range(len(coords))):
        raise ValueError('Boundary contains a zero-length edge')
    for i in range(len(coords)):
        for j in range(i+1,len(coords)):
            if j==i+1 or (i==0 and j==len(coords)-1):
                continue
            if segments_intersect(coords[i],coords[(i+1)%len(coords)],
                                  coords[j],coords[(j+1)%len(coords)]):
                raise ValueError('Self-intersecting boundary polygon')
    return coords, pts[0][2]


def signed_area(points):
    return 0.5*sum(points[i][0]*points[(i+1)%len(points)][1]-
                   points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))


def length2(a,b):
    return (a[0]-b[0])**2+(a[1]-b[1])**2


def cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def point_on_segment(p,a,b):
    return abs(cross(a,b,p))<=EPS*max(1,math.sqrt(length2(a,b))) and \
           min(a[0],b[0])-EPS<=p[0]<=max(a[0],b[0])+EPS and \
           min(a[1],b[1])-EPS<=p[1]<=max(a[1],b[1])+EPS


def segments_intersect(a,b,c,d):
    c1,c2,c3,c4=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
    if (c1>EPS and c2<-EPS or c1<-EPS and c2>EPS) and \
       (c3>EPS and c4<-EPS or c3<-EPS and c4>EPS):
        return True
    return any((point_on_segment(p,u,v) for p,u,v in ((c,a,b),(d,a,b),(a,c,d),(b,c,d))))


def point_inside(p, poly):
    # Boundary points count as contained, so a zero-clearance touching building is allowed.
    inside=False
    x,y=p
    for i,a in enumerate(poly):
        b=poly[(i+1)%len(poly)]
        if point_on_segment(p,a,b):
            return True
        if (a[1]>y)!=(b[1]>y):
            hit_x=a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if hit_x>x:
                inside=not inside
    return inside


def segment_distance(a,b,c,d):
    if segments_intersect(a,b,c,d):
        return 0.0
    def p_to_seg(p,u,v):
        dx,dy=v[0]-u[0],v[1]-u[1]
        t=max(0,min(1,((p[0]-u[0])*dx+(p[1]-u[1])*dy)/(dx*dx+dy*dy)))
        return math.hypot(p[0]-(u[0]+t*dx),p[1]-(u[1]+t*dy))
    return min(p_to_seg(a,c,d),p_to_seg(b,c,d),p_to_seg(c,a,b),p_to_seg(d,a,b))


def edges(poly):
    return [(poly[i],poly[(i+1)%len(poly)]) for i in range(len(poly))]


def polygon_distance(poly_a,poly_b):
    # Check nesting first, otherwise two nested footprints report positive edge distance.
    if point_inside(poly_a[0],poly_b) or point_inside(poly_b[0],poly_a):
        return 0.0
    return min(segment_distance(a,b,c,d) for a,b in edges(poly_a) for c,d in edges(poly_b))


def entirely_inside(building,boundary):
    # Vertex-only tests are insufficient for concave boundaries.
    if not all(point_inside(p,boundary) for p in building):
        return False
    for a,b in edges(building):
        if not point_inside(((a[0]+b[0])/2,(a[1]+b[1])/2),boundary):
            return False
        for c,d in edges(boundary):
            # Any genuine, non-collinear crossing makes the footprint invalid.
            ca,cb=cross(a,b,c),cross(a,b,d)
            cc,cd=cross(c,d,a),cross(c,d,b)
            if ((ca>EPS and cb<-EPS) or (ca<-EPS and cb>EPS)) and \
               ((cc>EPS and cd<-EPS) or (cc<-EPS and cd>EPS)):
                return False
    return True


def rectangle(x,y,length,width,angle_deg):
    # Placement point is the local rectangle corner. Native Rotate must use this point.
    theta=math.radians(angle_deg)
    cs,sn=math.cos(theta),math.sin(theta)
    corners=((0,0),(length,0),(length,width),(0,width))
    return [(x+u*cs-v*sn,y+u*sn+v*cs) for u,v in corners]



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

def nearest_edge_angle(p,boundary):
    px,py=p
    best=None
    for a,b in edges(boundary):
        vx,vy=b[0]-a[0],b[1]-a[1]
        den=vx*vx+vy*vy
        if den<=EPS:continue
        t=max(0.0,min(1.0,((px-a[0])*vx+(py-a[1])*vy)/den))
        d2=(px-a[0]-t*vx)**2+(py-a[1]-t*vy)**2
        if best is None or d2<best[0]:
            best=(d2,math.degrees(math.atan2(vy,vx))%180.0)
    if best is None: raise ValueError('Cannot determine nearest edge')
    return best[1]



MM2=1000000.0

def expanded(value,n,key):
    if not isinstance(value,(list,tuple)): value=[value]*n
    if len(value)!=n: raise ValueError('%s: expected %d values, got %d'%(key,n,len(value)))
    return list(value)

def rows(xs,ys,zs,ls,ws,angles,floors,codes):
    xs=list(xs);n=len(xs)
    others=[expanded(v,n,k) for k,v in [('Y',ys),('Z',zs),('Lengths',ls),('Widths',ws),
                                         ('AnglesDeg',angles),('Floors',floors),('TypologyCodes',codes)]]
    data=[(float(x),float(y),float(z),float(l),float(w),float(a),int(f),int(c))
          for x,y,z,l,w,a,f,c in zip(xs,*others)]
    for x,y,z,l,w,a,f,c in data:
        if l<=0 or w<=0 or f<=0 or c not in (0,1,2,3,4,5,7):raise ValueError('Invalid building parameters')
    return data

def outline(row,arm):return footprint_parts(row[7],row[0],row[1],row[3],row[4],row[5],arm)[0]

def area(row,arm):
    o,h=footprint_parts(row[7],row[0],row[1],row[3],row[4],row[5],arm)
    return (abs(signed_area(o))-abs(signed_area(h)))/MM2

def valid_rows(rows_,boundary,clearance,arm, extra=0.0):
    polys=[outline(r,arm) for r in rows_]
    for p in polys:
        if not entirely_inside(p,boundary): return False
    for i in range(len(polys)):
        for j in range(i+1,len(polys)):
            if polygon_distance(polys[i],polys[j])+1e-6 < clearance+extra:return False
    return True

def poly_boundary_distance(poly,boundary):
    return min(segment_distance(a,b,c,d) for a,b in edges(poly) for c,d in edges(boundary))

def metrics(rs,site_m2,arm,ggf=1.0):
    a=[area(r,arm) for r in rs]
    bfz=100*sum(a)/site_m2 if site_m2>0 else 0
    bnz=100*sum(v*r[6] for v,r in zip(a,rs))*ggf/site_m2 if site_m2>0 else 0
    return bfz,bnz,sum(a),sum(v*r[6] for v,r in zip(a,rs))*ggf

def dominates(a,b):
    return all(x<=y+1e-10 for x,y in zip(a,b)) and any(x<y-1e-10 for x,y in zip(a,b))

def fast_sort(objectives):
    n=len(objectives); fronts=[]; dominated=[[] for _ in range(n)];counts=[0]*n
    for p in range(n):
        for q in range(p+1,n):
            if dominates(objectives[p],objectives[q]):dominated[p].append(q);counts[q]+=1
            elif dominates(objectives[q],objectives[p]):dominated[q].append(p);counts[p]+=1
    front=[i for i,c in enumerate(counts) if c==0]
    ranks=[-1]*n
    while front:
        fronts.append(front)
        nxt=[]
        for p in front:
            ranks[p]=len(fronts)-1
            for q in dominated[p]:
                counts[q]-=1
                if counts[q]==0:nxt.append(q)
        front=nxt
    return fronts,ranks

def crowding(front,objectives):
    d={i:0.0 for i in front}
    if len(front)<=2:
        for i in front:d[i]=float('inf')
        return d
    for dim in range(len(objectives[0])):
        ids=sorted(front,key=lambda i:objectives[i][dim]); low=objectives[ids[0]][dim]; high=objectives[ids[-1]][dim]
        d[ids[0]]=d[ids[-1]]=float('inf')
        if high-low>1e-12:
            for j in range(1,len(ids)-1):d[ids[j]]+=(objectives[ids[j+1]][dim]-objectives[ids[j-1]][dim])/(high-low)
    return d

def mutate(rs,rng,step,minfloor,maxfloor,allowed):
    out=list(rs)
    if not out:return out
    i=rng.randrange(len(out));r=list(out[i])
    action=rng.randrange(5)
    if action==0:r[0]=cm_round(r[0]+rng.choice((-1,1))*step)
    if action==1:r[1]=cm_round(r[1]+rng.choice((-1,1))*step)
    if action==2:r[3]=max(100.0,cm_round(r[3]+rng.choice((-1,1))*step))
    if action==3:r[4]=max(100.0,cm_round(r[4]+rng.choice((-1,1))*step))
    if action==4:r[6]=max(minfloor,min(maxfloor,r[6]+rng.choice((-1,1))))
    out[i]=tuple(r)
    return out
