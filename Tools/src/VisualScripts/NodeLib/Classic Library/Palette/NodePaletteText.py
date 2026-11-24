"""General-purpose Allplan Visual Scripting node to display an input string in the palette."""
from NodeUtil.NodeBase import NodeBase


def create_node(init_data):
    return NodePaletteText(init_data)


class NodePaletteText(NodeBase):
    def _create_output(self):
        params = self.build_ele
        value = params.InputText.value
        if value is None:
            text = ""
        elif isinstance(value, (list, tuple)):
            text = ", ".join(str(item) for item in value)
        else:
            text = str(value)
        params.DisplayedText.value = text if text else "–"
        params.OutputText.value = text
