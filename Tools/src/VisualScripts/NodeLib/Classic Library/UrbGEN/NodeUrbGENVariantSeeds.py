"""Produce reproducible deterministic seeds for alternative site schemes."""
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENVariantSeeds')

def create_node(init_data):
    return NodeUrbGENVariantSeeds(init_data)


def calculate_variantseeds(base_seed,count,stride):
    n=int(count)
    if n<0:raise ValueError('Count must be >= 0')
    start=int(base_seed);step=int(stride)
    if step==0:raise ValueError('Stride must be nonzero')
    return [start+i*step for i in range(n)], list(range(n))

class NodeUrbGENVariantSeeds(NodeBase):
    def _create_output(self):
        p=self.build_ele
        for k in ('Seeds', 'Indices'):
            self._set_init_node_output(getattr(p,k))
        try:
            result=calculate_variantseeds(p.BaseSeed.value, p.Count.value, p.Stride.value)
            for k,v in zip(('Seeds', 'Indices'), result):
                getattr(p,k).value=v
        except Exception as exc:
            self.error='UrbGEN VariantSeeds: '+str(exc)
