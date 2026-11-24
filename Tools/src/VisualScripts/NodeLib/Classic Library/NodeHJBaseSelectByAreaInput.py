"""
Base class for the HJ manual curve selection node.
"""

# pylint: disable=no-self-use

import NemAll_Python_IFW_Input as AllplanIFW
import NemAll_Python_Utility as AllplanUtil
import NemAll_Python_IFW_ElementAdapter as AllplanElementAdapter

from NodeUtil import NodeBaseInteractor, NodeObjectUtil


class NodeHJBaseSelectByAreaInput(NodeBaseInteractor):
    """
    Base class for manual selection, initialized in the idle state.
    """

    def __init__(self, init_data):
        """ initialize """

        super().__init__(init_data)

        build_ele = self.build_ele

        self.post_element_selection = None
        self.filters                = NodeObjectUtil.create_objects_list(build_ele.ObjectFilter.value)

        if not build_ele.Executed.value or not build_ele.AssociativeObject.value:
            return

        build_ele.SelectedObjects.value            = AllplanElementAdapter.BaseElementAdapterList()
        build_ele.SelectedGeometry.value           = []
        build_ele.AssociativeObjectTimeStamp.value = []

        for obj_uuid in NodeObjectUtil.create_objects_list(build_ele.AssociativeObjectUUID.value):
            obj_uuid = AllplanUtil.GUID.FromString(obj_uuid)

            ele = AllplanElementAdapter.BaseElementAdapter.FromGUID(obj_uuid, self.document)

            if not ele.IsNull():
                build_ele.SelectedObjects.value.append(ele)
                build_ele.SelectedGeometry.value.append(ele.GetModelGeometry())
                build_ele.AssociativeObjectTimeStamp.value.append(ele.GetTimeStamp())

        build_ele.Executed.value = True


    def clean_up(self):
        """ clean up the node """

        if self.post_element_selection:
            AllplanIFW.InputFunctionStarter.RemoveFunction()

        self.post_element_selection = None

        self.filters = NodeObjectUtil.create_objects_list(self.build_ele.ObjectFilter.value)

    def start(self):
        """
        Start the interactor

        Returns:
            True:  input started
            False: input is complete
        """

        build_ele = self.build_ele

        # Initialize the input prompt even when selection is idle.
        NodeBaseInteractor.start(self)

        new_filters = NodeObjectUtil.create_objects_list(build_ele.ObjectFilter.value)

        if build_ele.Executed.value:
            if self.filters is None:
                return False

            old_set = {str(sel_filter) for sel_filter in self.filters}
            new_set = {str(sel_filter) for sel_filter in new_filters}

            if not old_set.difference(new_set):
                if self.is_input_enabled():
                    self.execute()
                return False

        self.filters = new_filters

        self.reset()

        return True


    def init_locals(self):
        """ Checking for interactor restart """

        if self.build_ele.Executed.value:
            return

        self._reset()


    def on_cancel_function(self):
        """ cancel the input """

        self.clean_up()
        # A canceled selection must not restart automatically next time.
        self.build_ele.Executed.value = True

        return True


    def _set_objects_data(self, sel_elements):
        """ set the objects data """

        build_ele = self.build_ele

        self._set_init_node_output([build_ele.SelectedObjects, build_ele.SelectedGeometry])

        build_ele.SelectedObjects.value            = sel_elements
        build_ele.SelectedGeometry.value           = []
        build_ele.AssociativeObjectUUID.value      = []
        build_ele.AssociativeObjectTimeStamp.value = []

        for ele in sel_elements:
            build_ele.SelectedGeometry.value.append(ele.GetModelGeometry())
            build_ele.AssociativeObjectUUID.value.append(str(ele.GetModelElementUUID()))
            build_ele.AssociativeObjectTimeStamp.value.append(ele.GetTimeStamp())

        self.post_element_selection = None

        if not sel_elements:
            self._reset()
            return True

        build_ele.Executed.value = True

        return True


    def _create_output(self):
        """ execute the node """
        return


    def draw_preview(self):
        """ draw the preview """
        return
