"""Drawing-file selection for Allplan 2027 Visual Scripting.

The native selection dialog and VS output ports are preserved.
A picture resource button opens selection; SelectionHint shows the file number.
"""
import NemAll_Python_BaseElements as Allplan_BaseElements
from NodeUtil.NodeBase import NodeBase


def create_node(init_data):
    return NodeDrawingFileSelection(init_data)


class NodeDrawingFileSelection(NodeBase):

    @staticmethod
    def _selected(value):
        values = value if isinstance(value, (list, tuple)) else [value]
        for candidate in values:
            try:
                number = int(candidate)
                if number > 0:
                    return number
            except (TypeError, ValueError):
                continue
        return 0

    def on_control_event(self, event_id):
        if event_id != 100:
            return

        previous = self._selected(self.build_ele.FileNumber.value)
        preselection = [previous] if previous > 0 else []
        chosen = Allplan_BaseElements.DrawingFileService.ShowDrawingFileDialog(
            self.document, True, False, preselection
        )
        if not chosen:
            return

        selected = self._selected(chosen)
        if selected <= 0:
            return

        self.build_ele.FileNumber.value = selected
        self._create_output()

    def _create_output(self):
        p = self.build_ele
        number = self._selected(p.FileNumber.value)
        p.FileNumber.value = number
        p.FileNumbers.value = [number] if number else []
        p.HasSelection.value = number > 0
        p.Executed.value = True
        p.SelectionHint.value = f"{number}" if number else "–"
        return True
