"""
HJ curve selection: wait for the palette button before selecting.
"""

# pylint: disable=no-self-use

import NemAll_Python_IFW_Input as AllplanIFW
from NodeUtil import NodeBase

from .NodeHJBaseSelectByAreaInput import NodeHJBaseSelectByAreaInput

NodeBase.trace_node_name('NodeHJSelectCurvesManual')


def create_node(init_data):
    """
    Create the node

    Args:
        init_data:  data for the node initialization
    """

    return NodeHJSelectCurvesManual(init_data)


class NodeHJSelectCurvesManual(NodeHJBaseSelectByAreaInput):
    """
    Manual curve selection with the original area filter.
    """

    def _reset(self):
        """
        Reset the input data
        """

        self.clean_up()

        build_ele = self.build_ele

        build_ele.Executed.value = False


        #----------------- define the curve filter

        def curve_filter(ele):
            if ele.IsNull():
                return False

            for filter in self.filters:
                if not filter(ele):
                    return False

            geometry = ele.GetGeometry()

            geo_type = str(type(geometry)).split(".")[-1].split("'")[0]

            return True if geo_type in ["Line3D", "Arc3D", "Polyline3D", "BSpline3D", "Spline3D", "Polygon3D", "Path3D",
                                        "Line2D", "Arc2D", "Polyline2D", "BSpline2D", "Spline2D", "Polygon2D", "Path2D"] else False


        #----------------- set the filter and start the selection

        sel_query   = AllplanIFW.SelectionQuery([curve_filter])
        sel_setting = AllplanIFW.ElementSelectFilterSetting(sel_query, True)

        self.post_element_selection = AllplanIFW.PostElementSelection()

        AllplanIFW.InputFunctionStarter.StartElementSelect(self.display_text, sel_setting, self.post_element_selection, False)


    def process_mouse_msg(self, _mouse_msg, _pnt, _msg_info):
        """
        Process the mouse message event

        Args:
            mouse_msg:  the mouse message.
            pnt:        the input point in view coordinates
            msg_info:   additional message info.

        Returns:
            True/False for success.
        """

        if self.post_element_selection is None:
            return True

        self._set_objects_data(self.post_element_selection.GetSelectedElements(self.coord_input.GetInputViewDocument()))

        # Re-enable downstream evaluation after the initial run without a
        # boundary. Do not restart the script from inside a mouse callback:
        # restarting changes the current node index while it is still in use.
        if self.build_ele.Executed.value and self.build_ele.SelectedGeometry.value:
            self._resume_downstream_evaluation()

        return True


    def _resume_downstream_evaluation(self):
        """Mirror the skip_eval reset in NodeScript.update_elements.

        NodeScript.process_mouse_msg will continue with is_next_node after this
        callback returns, so the framework can execute the graph normally.
        """
        callback = self.enable_need_update
        script = getattr(callback, "__self__", None)
        elements = getattr(script, "build_ele_list", None)

        if elements is None:
            print("HJ Select Curves Manual: NodeScript element list unavailable")
            return

        # NodeInitData uses a zero-based graph index, while build_ele_list
        # includes the root script at index zero. Verify the object identity.
        index = self.node_index + 1
        if index >= len(elements) or elements[index] is not self.build_ele:
            index = next((i for i, element in enumerate(elements)
                          if element is self.build_ele), -1)
        if index < 1:
            print("HJ Select Curves Manual: selection node not found")
            return

        reset_count = 0
        for element in elements[index + 1:]:
            if element.skip_eval:
                reset_count += 1
            element.skip_eval = False

        callback()
        print(f"HJ Select Curves Manual: re-enabled {reset_count} downstream nodes")
