"""Resolve all pairwise collisions greedily in input order; invalid checks block output."""
from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENCollisionResolver')

def create_node(init_data):
    return NodeUrbGENCollisionResolver(init_data)


def calculate_collisionresolver(count, index_a, index_b, collision_states, valid_results):
    n=int(count)
    if n<0: raise ValueError('Count must be >= 0')
    lists=[list(x) for x in (index_a,index_b,collision_states,valid_results)]
    if len(set(map(len,lists))) != 1: raise ValueError('All pair arrays must have identical lengths')
    a,b,coll,valid=lists
    expected=n*(n-1)//2
    if len(a)!=expected: raise ValueError('Expected %d pairs, got %d' % (expected,len(a)))
    if not all(bool(v) for v in valid):
        # Fail closed: no building can be accepted on incomplete geometric checks.
        return [False]*n,[-2]*n,[],False
    collisions=set(); seen=set()
    for i,j,hit in zip(a,b,coll):
        i,j=int(i),int(j)
        if i<0 or j>=n or i>=j or (i,j) in seen:raise ValueError('Malformed or duplicated pair indices')
        seen.add((i,j))
        if bool(hit):collisions.add((i,j))
    keep=[False]*n;rejected=[-1]*n;accepted=[]
    for j in range(n):
        blocker=next((i for i in accepted if (i,j) in collisions),None)
        if blocker is None:
            keep[j]=True;accepted.append(j)
        else: rejected[j]=blocker
    return keep,rejected,accepted,True

class NodeUrbGENCollisionResolver(NodeBase):
    def _create_output(self):
        p=self.build_ele
        for k in ('KeepStates', 'RejectedBy', 'AcceptedIndices', 'IsValid'):
            self._set_init_node_output(getattr(p,k))
        try:
            result=calculate_collisionresolver(p.Count.value, p.IndexA.value, p.IndexB.value, p.CollisionStates.value, p.ValidResults.value)
            for k,v in zip(('KeepStates', 'RejectedBy', 'AcceptedIndices', 'IsValid'), result):
                getattr(p,k).value=v
        except Exception as exc:
            self.error='UrbGEN CollisionResolver: '+str(exc)
