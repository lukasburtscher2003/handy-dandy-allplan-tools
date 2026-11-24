"""
HJ GeometryElement: empty-input-safe variant of the Allplan 2027 node.
"""

import NemAll_Python_BaseElements as AllplanBaseElements
import NemAll_Python_BasisElements as AllplanBasisElements
import NemAll_Python_Utility as AllplanUtil

from NodeUtil import NodeBase, NodeFunctionUtil, NodeParameterTest, DefaultValue

from Palettes.Layout.Area2DProperties import Area2DProperties

NodeBase.trace_node_name('NodeHJGeometryElement')


def create_node(init_data):
    """
    Create the node

    Args:
        init_data:  data for the node initialization
    """

    return NodeHJGeometryElement(init_data)


def _has_geometry(value):
    """Return False for an empty or entirely empty nested geometry list."""
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return any(_has_geometry(item) for item in value)
    return True


class NodeHJGeometryElement(NodeBase):
    """
    GeometryElement with explicit handling of missing geometry.
    """

    def _create_output(self):
        """ create the output """

        build_ele = self.build_ele

        self._set_init_node_output(self.build_ele.Element)

        if build_ele.GeometryElement.value != []:
            build_ele.Object.Value = build_ele.GeometryElement.value

        # During initial activation, no footprints may exist yet. Allplan's
        # list utility cannot repeat the last item of an empty data list.
        if not _has_geometry(build_ele.Object.value):
            build_ele.Element.value = []
            return

        if NodeParameterTest.test_empty_parameter(self, build_ele, "", "Object"):
            return

        def create_model_element(geo_ele,
                                 com_prop: AllplanBaseElements.CommonProperties,
                                 area_prop: Area2DProperties,
                                 attributes):
            if com_prop == DefaultValue.USE_DEFAULT_VALUE:
                com_prop = AllplanBaseElements.CommonProperties()

                com_prop.GetGlobalProperties()

            surface = getattr(com_prop, "Surface", None)

            if surface is not None:
                texturedef = AllplanBasisElements.TextureDefinition(surface)

                model_ele = AllplanBasisElements.ModelElement3D(com_prop, texturedef, geo_ele)
            else:
                model_ele = AllplanBasisElements.ModelElement3D(com_prop, geo_ele)


            #---------------- add the attributes

            attr_list = []

            if attributes and attributes[0] != DefaultValue.USE_DEFAULT_VALUE:
                attribute_type = AllplanBaseElements.AttributeService

                for attr_id, attr_value in attributes:
                    value_type = AllplanBaseElements.AttributeService.GetAttributeType(self.document, attr_id)

                    if value_type == attribute_type.Integer:
                        attr_list.append(AllplanBaseElements.AttributeInteger(attr_id, attr_value))

                    elif value_type == attribute_type.Double:
                        attr_list.append(AllplanBaseElements.AttributeDouble(attr_id, attr_value))

                    elif value_type == attribute_type.String:
                        attr_list.append(AllplanBaseElements.AttributeString(attr_id, attr_value))

                    elif value_type == attribute_type.Enum:
                        enum_id = AllplanBaseElements.AttributeService.GetEnumIDFromValueString(attr_id, str(attr_value))

                        if enum_id == -1:
                            AllplanUtil.ShowMessageBox("Index for enumeration attribute '" + str(attr_value) + "' not found",
                                                    AllplanUtil.MB_OK)
                        else:
                            attr_list.append(AllplanBaseElements.AttributeEnum(attr_id, enum_id))
                    else:
                        AllplanUtil.ShowMessageBox("Missing implementation for attribute value type '" + str(value_type) + "'",
                                                AllplanUtil.MB_OK)


            #---------------- add the surface attributes

            if area_prop != DefaultValue.USE_DEFAULT_VALUE:
                if area_prop.is_filling:
                    attr_list.append(AllplanBaseElements.AttributeInteger(252, area_prop.filling_color))

                if area_prop.is_hatching:
                    attr_list.append(AllplanBaseElements.AttributeInteger(118, 2))
                    attr_list.append(AllplanBaseElements.AttributeInteger(124, area_prop.hatching_id))

                elif area_prop.is_pattern:
                    attr_list.append(AllplanBaseElements.AttributeInteger(118, 1))
                    attr_list.append(AllplanBaseElements.AttributeInteger(126, area_prop.pattern_id))

                elif area_prop.is_face_style:
                    attr_list.append(AllplanBaseElements.AttributeInteger(125, area_prop.face_style_id))

                elif area_prop.is_filling:
                    attr_list.append(AllplanBaseElements.AttributeInteger(118, 3))

                elif area_prop.is_bitmap:
                    attr_list.append(AllplanBaseElements.AttributeString(333, ""))
                    attr_list.append(AllplanBaseElements.AttributeString(336, area_prop.bitmap_name))

            if not attr_list:
                return model_ele

            attr_set_list = []
            attr_set_list.append(AllplanBaseElements.AttributeSet(attr_list))

            model_ele.SetAttributes(AllplanBaseElements.Attributes(attr_set_list))

            return model_ele

        self.build_ele.Element.value = \
            NodeFunctionUtil.execute_for_lists_with_block(create_model_element,
                                                          build_ele.Object,
                                                          build_ele.FormatProperties,
                                                          build_ele.Area2DProperties,
                                                          (build_ele.Attributes, True),
                                                          set_empty_value_default = DefaultValue.USE_DEFAULT_VALUE)
