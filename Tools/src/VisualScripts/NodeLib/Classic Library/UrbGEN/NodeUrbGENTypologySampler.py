"""Select building typology IDs reproducibly from seven user-specified weights."""
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENTypologySampler')

def create_node(init_data):
    return NodeUrbGENTypologySampler(init_data)


import math
import random

def calculate_typologysampler(count,weights,seed):
    n=int(count)
    if n<0: raise ValueError('Count must be >= 0')
    w=[float(v) for v in weights]
    if len(w)!=7 or any(not math.isfinite(v) or v<0 for v in w) or sum(w)<=0:raise ValueError('Weights must be 7 nonnegative numbers with a positive sum')
    rng=random.Random(int(seed));ids=rng.choices(range(7),weights=w,k=n)
    names=['I','L','T','H','U','Cross','Courtyard']
    return ids,[names[i] for i in ids]

class NodeUrbGENTypologySampler(NodeBase):
    def _create_output(self):
        p=self.build_ele
        for k in ('TypologyIds', 'TypologyNames'):
            self._set_init_node_output(getattr(p,k))
        try:
            result=calculate_typologysampler(p.Count.value, p.Weights.value, p.Seed.value)
            for k,v in zip(('TypologyIds', 'TypologyNames'), result):
                getattr(p,k).value=v
        except Exception as exc:
            self.error='UrbGEN TypologySampler: '+str(exc)
