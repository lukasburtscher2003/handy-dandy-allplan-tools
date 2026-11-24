"""Expand per-building massing parameters into per-level parameter lists.
Does not create geometry. Native VS nodes make the level footprints/extrusions.
"""
from NodeUtil import NodeBase
NodeBase.trace_node_name('NodeUrbGENLevelSchedule')
def create_node(init_data):return NodeUrbGENLevelSchedule(init_data)

def expand(v,n,name):
    if not isinstance(v,(list,tuple)):return [v]*n
    if len(v)!=n:raise ValueError(name+' length must match building count')
    return v

class NodeUrbGENLevelSchedule(NodeBase):
    def _create_output(self):
        b=self.build_ele
        fields=('BuildingIndex','FloorIndex','LevelX','LevelY','LevelZ','LevelLengths','LevelWidths','LevelAnglesDeg',
                'FloorHeights','LevelTypologyCodes','IsPodium','IsValid','ErrorMessage')
        for k in fields:self._set_init_node_output(getattr(b,k))
        try:
            xs=list(b.X.value); n=len(xs)
            src={k:expand(getattr(b,k).value,n,k) for k in ('Y','Z','Lengths','Widths','AnglesDeg','Floors','TypologyCodes')}
            h=float(b.FloorHeight.value); podium=int(b.PodiumFloors.value)
            if h<=0:raise ValueError('FloorHeight must be positive')
            if podium<0:raise ValueError('PodiumFloors must be >=0')
            ans={k:[] for k in fields[:-2]}
            for i,x in enumerate(xs):
                nlevels=int(src['Floors'][i]);
                if nlevels<1 or nlevels>200:raise ValueError('Floors must be 1..200')
                for j in range(nlevels):
                    vals={'BuildingIndex':i,'FloorIndex':j,'LevelX':float(x),'LevelY':float(src['Y'][i]),
                      'LevelZ':float(src['Z'][i])+j*h,'LevelLengths':float(src['Lengths'][i]),
                      'LevelWidths':float(src['Widths'][i]),'LevelAnglesDeg':float(src['AnglesDeg'][i]),
                      'FloorHeights':h,'LevelTypologyCodes':int(src['TypologyCodes'][i]),
                      'IsPodium':j<podium}
                    for k,v in vals.items():ans[k].append(v)
            for k,v in ans.items():getattr(b,k).value=v
            b.IsValid.value=True;b.ErrorMessage.value=''
        except Exception as exc:
            b.IsValid.value=False;b.ErrorMessage.value=str(exc);self.error='LevelSchedule: '+str(exc)
