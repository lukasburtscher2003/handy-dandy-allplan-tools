"""Generate deterministic candidate XY coordinates inside a bounding rectangle; filter by native site containment before use."""
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENSeededPoints')

def create_node(init_data):
    return NodeUrbGENSeededPoints(init_data)


import math
import random

def calculate_seededpoints(count,min_x,max_x,min_y,max_y,z,seed,min_distance,max_attempts):
    n=int(count);attempts=int(max_attempts)
    coords=[float(t) for t in (min_x,max_x,min_y,max_y,z,min_distance)]
    if not all(math.isfinite(v) for v in coords):raise ValueError('Coordinates must be finite')
    x0,x1,y0,y1,level,sep=coords
    if n<0 or attempts<0 or x1<=x0 or y1<=y0 or sep<0:raise ValueError('Invalid extent, count, or minimum spacing')
    rng=random.Random(int(seed));points=[]
    if sep>0:
        # Uniform rejection sampling; fast enough for small conceptual sites.
        for k in range(attempts):
            if len(points)>=n:break
            candidate=(rng.uniform(x0,x1),rng.uniform(y0,y1))
            if all((candidate[0]-x)**2+(candidate[1]-y)**2>=sep**2 for x,y in points):points.append(candidate)
    else:
        points=[(rng.uniform(x0,x1),rng.uniform(y0,y1)) for _ in range(n)]
    return [p[0] for p in points],[p[1] for p in points],[level]*len(points),len(points),len(points)==n

class NodeUrbGENSeededPoints(NodeBase):
    def _create_output(self):
        p=self.build_ele
        for k in ('X', 'Y', 'ZValues', 'Generated', 'Complete'):
            self._set_init_node_output(getattr(p,k))
        try:
            result=calculate_seededpoints(p.Count.value, p.MinX.value, p.MaxX.value, p.MinY.value, p.MaxY.value, p.Z.value, p.Seed.value, p.MinDistance.value, p.MaxAttempts.value)
            for k,v in zip(('X', 'Y', 'ZValues', 'Generated', 'Complete'), result):
                getattr(p,k).value=v
        except Exception as exc:
            self.error='UrbGEN SeededPoints: '+str(exc)
