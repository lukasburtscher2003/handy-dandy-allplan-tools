"""Generic Visual Scripting variant navigation palette control (Allplan 2027)."""
from NodeUtil.NodeBase import NodeBase


def create_node(init_data):
    return NodeVariantNavigation(init_data)


class NodeVariantNavigation(NodeBase):
    """Palette arrows adjust a zero-based output index, without geometry logic."""

    EVENT_PREVIOUS = 100
    EVENT_NEXT = 101

    def _refresh_values(self):
        count = max(1, int(self.build_ele.VariantCount.value or 1))
        index = int(self.build_ele.CurrentVariant.value or 0)
        index = max(0, min(index, count - 1))
        self.build_ele.CurrentVariant.value = index
        self.build_ele.VariantDisplay.value = "{} / {}".format(index + 1, count)
        return count, index

    def _create_output(self):
        self._refresh_values()

    def on_control_event(self, event_id):
        count, index = self._refresh_values()
        if event_id == self.EVENT_PREVIOUS:
            index = max(0, index - 1)
        elif event_id == self.EVENT_NEXT:
            index = min(count - 1, index + 1)
        else:
            return False
        self.build_ele.CurrentVariant.value = index
        self.build_ele.VariantDisplay.value = "{} / {}".format(index + 1, count)
        # Same pattern as native VS event-driven nodes.
        self.execute()
        return True
