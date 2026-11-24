"""Display an input string as a full-width, read-only text in the VS palette."""
from NodeUtil.NodeBase import NodeBase


def create_node(init_data):
    return NodeInfoTextBlock(init_data)


class NodeInfoTextBlock(NodeBase):
    def _create_output(self):
        params = self.build_ele
        incoming = params.InputText.value
        if incoming is None:
            text = ""
        elif isinstance(incoming, (list, tuple)):
            text = "\n".join(str(item) for item in incoming)
        else:
            text = str(incoming)
        params.DisplayText.value = text
        params.Executed.value = True
        return True
