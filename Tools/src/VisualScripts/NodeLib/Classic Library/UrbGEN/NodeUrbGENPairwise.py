"""UrbGEN: create all unique object pairs for a native Visual Scripting collision check."""

from NodeUtil import NodeBase

NodeBase.trace_node_name('NodeUrbGENPairwise')


def create_node(init_data):
    return NodeUrbGENPairwise(init_data)


def make_pairs(objects):
    """Return parallel item/index lists, no (i,i) or duplicated reversed pairs."""
    values = list(objects)
    a, b, ia, ib = [], [], [], []
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            a.append(values[i])
            b.append(values[j])
            ia.append(i)
            ib.append(j)
    return a, b, ia, ib


class NodeUrbGENPairwise(NodeBase):
    """Expand one one-dimensional list into all unique unordered pairs."""

    def _create_output(self):
        build_ele = self.build_ele
        for output in (build_ele.ObjectsA, build_ele.ObjectsB,
                       build_ele.IndexA, build_ele.IndexB):
            self._set_init_node_output(output)

        objects = build_ele.Objects.value
        if objects is None:
            self.warning = 'Objects input missing'
            return
        if not isinstance(objects, (list, tuple)):
            self.error = 'Objects must be a one-dimensional list'
            return
        if len(objects) < 2:
            build_ele.ObjectsA.value = []
            build_ele.ObjectsB.value = []
            build_ele.IndexA.value = []
            build_ele.IndexB.value = []
            return

        a, b, ia, ib = make_pairs(objects)
        build_ele.ObjectsA.value = a
        build_ele.ObjectsB.value = b
        build_ele.IndexA.value = ia
        build_ele.IndexB.value = ib
