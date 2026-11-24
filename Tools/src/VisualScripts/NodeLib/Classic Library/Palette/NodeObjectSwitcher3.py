
"""
Script for NodeObjectSwitcher3
"""

from NodeUtil import NodeObjectUtil, NodeBase


NodeBase.trace_node_name('NodeObjectSwitcher3')


def create_node(init_data):
    """
    Create the node

    Args:
        init_data:  data for the node initialization
    """

    return NodeObjectSwitcher3(init_data)


class NodeObjectSwitcher3(NodeBase):
    """
    Definition of class NodeObjectSwitcher3
    """

    def _create_output(self):
        """
        Switch the values
        """

        if self.build_ele.ListSelector.value == 1:
            self.build_ele.Objects.value = NodeObjectUtil.create_objects_list(self.build_ele.Objects1.value)

        elif self.build_ele.ListSelector.value == 2:
            self.build_ele.Objects.value = NodeObjectUtil.create_objects_list(self.build_ele.Objects2.value)

        else:
            self.build_ele.Objects.value = NodeObjectUtil.create_objects_list(self.build_ele.Objects3.value)

        NodeObjectUtil.create_model_objects(self.build_ele.Objects.value, self.build_ele, self.com_prop)
        NodeObjectUtil.create_model_preview_objects(self.build_ele.Objects.value, self.build_ele, self.preview_com_prop)
