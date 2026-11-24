"""
Script for NodeCheckboxInput
"""

#pylint: disable=R0201

from NodeUtil.NodeBase import NodeBase


NodeBase.trace_node_name('NodeCheckboxInput')


def create_node(init_data):
    """
    Create the node

    Args:
        init_data:  data for the node initialization
    """

    return NodeCheckboxInput(init_data)


class NodeCheckboxInput(NodeBase):
    """
    Definition of class NodeCheckboxInput
    """

    def _create_output(self):
        """ Execute the node """
        return


    def modify_element_property(self, page, name, value):
        """
        Modify element property and execute the node output and object creation

        Args:
            page:   the page of the property
            name:   the name of the property.
            value:  new value for property.
        """

        super().modify_element_property(page, name, value)

        return True
