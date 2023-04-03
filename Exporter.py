# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import json
import math
import inspect
from collections import OrderedDict

from . import template as _MP
from .template import KeyNames as _keyNames

from . import Utilities as util
from . import Settings


class Exporter:

    def __init__(self):
        self.node_info_to_id_dict = {}
        self.exporters = {
            _MP.AType.NODE: self._export_node_connection,
            _MP.AType.NODE_LIST: self._export_node_list,
            _MP.AType.CURVE: self._export_curve,
            _MP.AType.OBJECT: self._export_object,
            _MP.AType.OBJECT_LIST: self._export_object_list,
            _MP.AType.STRING: self._export_string,
            _MP.AType.INT: self._export_int,
            _MP.AType.FLOAT: self._export_float,
            _MP.AType.FLOAT_PERCENTAGE: self._export_float_percentage,
            _MP.AType.FLOAT_ANGLE: self._export_float_angle,
            _MP.AType.FLOAT_WITH_SCALE: self._export_float_with_scale,
            _MP.AType.BOOL: self._export_bool,
            _MP.AType.ENUM: self._export_enum,
            _MP.AType.FLOAT_VECTOR_2: self._export_float_vector_2,
            _MP.AType.COLOR: self._export_color,
            _MP.AType.IMAGE: self._export_image,
            _MP.AType.GRADATION: self._export_gradation,
            _MP.AType.MATERIAL: self._export_material,
            _MP.AType.MATERIAL_LIST: self._export_material_list,
            _MP.AType.ADVANCED_MATERIAL: self._export_advanced_material,
            _MP.AType.USERDEF: self._export_userdef,
            _MP.AType.NOT_IMPLEMENTED: self._export_not_implemented
        }

        self.node_types = dict((cls._blenderNodeName, cls) for _, cls
                               in inspect.getmembers(_MP, inspect.isclass)
                               if issubclass(cls, _MP.Node) and cls.is_blender_node())

    def export_to_json_string(self):
        """
            PencilノードをJSONにエクスポートする
            :return: PencilノードをシリアライズしたJSON文字列
        """

        json_dict = OrderedDict()
        json_dict[_keyNames.PLATFORM] = f"Blender {bpy.app.version_string}"
        json_dict[_keyNames.FILE_VERSION] = Settings.FILE_VERSION
        json_dict[_keyNames.SCALE_FACTOR] = Settings.BLENDER_SCALE_FACTOR
        json_dict[_keyNames.LINES] = self._create_node_dict()
        json_dict[_keyNames.MATERIALS] = self._create_material_dict()

        return json.dumps(json_dict, indent=4, ensure_ascii=False)

    def _create_node_dict(self):
        node_list = util.enumerate_all_nodes()
        nodes = OrderedDict()
        for node in node_list:
            node_params_def = self.node_types[node.__class__.__name__]
            a_node_dict = OrderedDict()
            a_node_dict[_keyNames.NODE_NAME] = node.name
            a_node_dict[_keyNames.NODE_TYPE] = node_params_def.get_node_to_export_name()
            a_node_dict[_keyNames.NODE_LOCATION] = (node.location.x, node.location.y)
            a_node_dict[_keyNames.PARAMS] = OrderedDict()
            for json_param_name, (attr_name, attr_type) in node_params_def.get_params():
                a_node_dict[_keyNames.PARAMS][json_param_name] = self.exporters[attr_type](node, attr_name)
            # Texture Map NodeはUnity版との相互運用のため特別な処理が必要
            if a_node_dict[_keyNames.NODE_TYPE] == "TextureMap":
                self._modify_texture_map_node(a_node_dict)
            nodes[f"{node.tree_from_node().name}/{node.name}"] = a_node_dict
        return nodes

    def _create_material_dict(self):
        material_and_line_functions_list = util.enumerate_material_and_line_functions()
        materials = OrderedDict()
        for mat, line_functions_node in material_and_line_functions_list:
            materials[mat.name_full] = \
                util.create_pencil_material_dummy(mat.name_full, mat.pcl4_line_functions.name_full)
            a_line_functions_dict = OrderedDict()
            a_line_functions_dict[_keyNames.NODE_NAME] = mat.pcl4_line_functions.name_full
            a_line_functions_dict[_keyNames.NODE_TYPE] = _MP.MaterialLineFunctionsNode.get_node_to_export_name()
            a_line_functions_dict[_keyNames.PARAMS] = OrderedDict()
            for json_param_name, (attr_name, attr_type) in _MP.MaterialLineFunctionsNode.get_params():
                a_line_functions_dict[_keyNames.PARAMS][json_param_name] = \
                    self.exporters[attr_type](line_functions_node, attr_name)
            materials[mat.pcl4_line_functions.name_full] = a_line_functions_dict
        return materials

    """
    Exporters
    """

    def _export_node_connection(self, node, prop_name):
        socket_id = node.bl_rna.properties[prop_name].default
        child_node = next((x.get_connected_node() for x in node.inputs if x.identifier == socket_id), None)
        return f"{child_node.tree_from_node().name}/{child_node.name}" if child_node is not None else None

    def _export_node_list(self, node, prop_name):
        socket_id = node.bl_rna.properties[prop_name].default
        child_nodes = (x.get_connected_node() for x in node.inputs if x.identifier.startswith(socket_id))
        return [f"{x.tree_from_node().name}/{x.name}" for x in child_nodes if x is not None]

    def _export_curve(self, node, prop_name):
        curve_points = util.get_curve_points(node, getattr(node, prop_name))
        universal_curve = util.make_universal_curve(node, getattr(node, prop_name))
        ret = OrderedDict()
        ret[_keyNames.BLENDER_CURVE_KEYS] = curve_points
        ret[_keyNames.UNIVERSAL_CURVE_KEYS] = universal_curve
        return ret

    def _export_object(self, node, prop_name):
        obj = getattr(node, prop_name)
        return obj.name if obj is not None else None

    def _export_object_list(self, node, prop_name):
        return [x.content.name for x in getattr(node, prop_name) if x is not None]

    def _export_string(self, node, prop_name):
        return getattr(node, prop_name)

    def _export_int(self, node, prop_name):
        return getattr(node, prop_name)

    def _export_float(self, node, prop_name):
        return getattr(node, prop_name)

    def _export_float_percentage(self, node, prop_name):
        #  Blender: percentage -> JSON: raw value
        percentage_value = getattr(node, prop_name)
        return percentage_value / 100.0

    def _export_float_angle(self, node, prop_name):
        #  Blender: radian -> JSON: degree
        rad_value = getattr(node, prop_name)
        return math.degrees(rad_value)

    def _export_float_with_scale(self, node, prop_name):
        return getattr(node, prop_name)

    def _export_bool(self, node, prop_name):
        return getattr(node, prop_name)

    def _export_enum(self, node, prop_name):
        enum_str = getattr(node, prop_name)
        enum_items = node.bl_rna.properties[prop_name].enum_items
        return next(x.value for x in enum_items if x.identifier == enum_str)

    def _export_float_vector_2(self, node, prop_name):
        vector2 = getattr(node, prop_name)
        return [vector2.x, vector2.y]

    def _export_color(self, node, prop_name):
        color = getattr(node, prop_name)
        srgb_color = util.linear_to_srgb([color.r, color.g, color.b])
        return [srgb_color[0], srgb_color[1], srgb_color[2], 1.0]

    def _export_image(self, node, prop_name):
        image = getattr(node, prop_name)
        return image.name if image is not None else None

    def _export_gradation(self, node, prop_name):
        pass

    def _export_material(self, node, prop_name):
        return {
            "Name": getattr(node, prop_name).name,
            "Id": None,
            "MaterialType": "Other"
        }

    def _export_material_list(self, node, prop_name):
        return [{"Name": x.content.name,
                 "Id": None,
                 "MaterialType": "Other"} for x in getattr(node, prop_name)]

    def _export_advanced_material(self, node, prop_name):
        pass

    def _export_userdef(self, node, prop_name):
        pass

    def _export_not_implemented(self, *_):
        pass

    """
    for Other Format (e.g. Unity)
    """

    def _modify_texture_map_node(self, node_dict):
        extended_texture_uv = node_dict["Params"]["ExtendedTextureUV"]
        uv_selection_mode = node_dict["Params"]["UVSelectionMode"]
        uv_index = node_dict["Params"]["UVIndex"]
        if extended_texture_uv == 0:  # Screen
            original_texture_uv = 0  # Screen
        elif uv_selection_mode == 1:  # Name
            original_texture_uv = 1  # MeshObject1
        elif uv_index > 3:
            original_texture_uv = 4  # MeshObject4
        else:
            original_texture_uv = uv_index + 1
        node_dict["Params"]["TextureUV"] = original_texture_uv
