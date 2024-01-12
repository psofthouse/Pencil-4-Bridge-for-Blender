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
            _MP.AType.BOOL_LIST_8: self._export_bool_list_8,
            _MP.AType.ENUM: self._export_enum,
            _MP.AType.FLOAT_VECTOR_2: self._export_float_vector_2,
            _MP.AType.COLOR: self._export_color,
            _MP.AType.IMAGE: self._export_image,
            _MP.AType.GRADATION: self._export_gradation,
            _MP.AType.MATERIAL: self._export_material,
            _MP.AType.MATERIAL_LIST: self._export_material_list,
            _MP.AType.ADVANCED_MATERIAL: self._export_advanced_material,
            _MP.AType.USERDEF: self._export_userdef,
            _MP.AType.POSITION_GROUP: self._export_string,
            _MP.AType.COLOR_GROUP: self._export_string,
            _MP.AType.FLOAT_ARRAY_STRING: self._export_float_array_string,
            _MP.AType.COLOR_ARRAY_STRING: self._export_color_array_string,
            _MP.AType.NOT_IMPLEMENTED: self._export_not_implemented
        }

        self.node_types = dict((cls._blenderNodeName, cls) for _, cls
                               in inspect.getmembers(_MP, inspect.isclass)
                               if issubclass(cls, _MP.Node) and cls.is_blender_node())
        
        self.context = None

    def export_to_json_string(self, context):
        """
            PencilノードをJSONにエクスポートする
            :return: PencilノードをシリアライズしたJSON文字列
        """
        
        self.context = context
        json_dict = OrderedDict()
        json_dict[_keyNames.PLATFORM] = f"Blender {bpy.app.version_string}"
        json_dict[_keyNames.FILE_VERSION] = Settings.FILE_VERSION
        json_dict[_keyNames.SCALE_FACTOR] = Settings.BLENDER_SCALE_FACTOR
        json_dict[_keyNames.LINES] = self._create_node_dict()
        json_dict[_keyNames.MATERIALS] = self._create_material_dict()
        position_group_dict, color_group_dict = self._create_groupd_dict()
        json_dict[_keyNames.POSITION_GROUP] = position_group_dict
        json_dict[_keyNames.COLOR_GROUP] = color_group_dict

        return json.dumps(json_dict, indent=4, ensure_ascii=False)

    def _export_node_params(self, params_dict: OrderedDict, node, node_params_def):
        for json_param_name, (attr_name, attr_type) in node_params_def.get_params():
            params_dict[json_param_name] = self.exporters[attr_type](node, attr_name)

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
            self._export_node_params(a_node_dict[_keyNames.PARAMS], node, node_params_def)
            # Texture Map NodeはUnity版との相互運用のため特別な処理が必要
            if a_node_dict[_keyNames.NODE_TYPE] == "TextureMap":
                self._modify_texture_map_node(a_node_dict)
            nodes[f"{node.tree_from_node().name}/{node.name}"] = a_node_dict
        return nodes

    def _create_groupd_dict(self):
        groups_def = (
            (OrderedDict(), _MP.PositionGroupNode, "is_pcl4_position_group"),
            (OrderedDict(), _MP.ColorGroupNode, "is_pcl4_color_group"),
        )
        # 位置グループ・カラーグループを出力
        for groups, node_params_def, check_property_name in groups_def:
            for tree in bpy.data.node_groups:
                if getattr(tree, check_property_name, False):
                    a_group_dict = OrderedDict()
                    groups[tree.name_full] = a_group_dict
                    a_group_dict[_keyNames.NODE_NAME] = tree.name_full
                    a_group_dict[_keyNames.PARAMS] = OrderedDict()
                    self._export_node_params(a_group_dict[_keyNames.PARAMS], tree, node_params_def)
        return (groups_def[0][0], groups_def[1][0])

    def _create_material_dict(self):
        material_names = set(bpy.data.materials.keys())
        materials = OrderedDict()
        # Pencil+ マテリアルを出力
        for mat in (x for x in bpy.data.materials if getattr(x, "is_pcl4_material", False)):
            a_material_dict = OrderedDict()
            materials[mat.name_full] = a_material_dict
            a_material_dict[_keyNames.NODE_NAME] = mat.name_full
            a_material_dict[_keyNames.NODE_TYPE] = _MP.PencilMaterialNode.get_node_to_export_name()
            a_material_dict[_keyNames.PARAMS] = OrderedDict()
            self._export_node_params(a_material_dict[_keyNames.PARAMS], mat, _MP.PencilMaterialNode)
            # グラデーションの出力
            a_gradation_dict = OrderedDict()
            a_material_dict[_keyNames.PARAMS]["Gradation"] = a_gradation_dict
            gradation_params = dict()
            for _, (attr_name, attr_type) in _MP.MaxGradation.get_params():
                if attr_type == _MP.AType.NOT_IMPLEMENTED:
                    continue
                s = getattr(mat, attr_name)
                gradation_params[attr_name] = [eval(attr_type)(x) for x in s.split(",")] if attr_type != _MP.AType.COLOR else\
                    [util.linear_to_srgb([float(y) for y in x.split(",")]) + [1.0] for x in s.split(";")]
            max_gradation = []
            a_gradation_dict["MaxGradation"] = max_gradation
            for i in range(mat.pcl4mtl_num_zones):
                a_zone_dict = OrderedDict()
                max_gradation.append(a_zone_dict)
                for json_param_name, (attr_name, attr_type) in _MP.MaxGradation.get_params():
                    a_zone_dict[json_param_name] = gradation_params[attr_name][i] if attr_name in gradation_params else None
            universal_gradation = []
            a_gradation_dict["UniversalGradation"] = universal_gradation
            for i in range(mat.pcl4mtl_num_zones):
                zone = max_gradation[i]
                def create_universal_zone_dict(zone, position, interpolation) -> OrderedDict:
                    univaersal_zone_dict = OrderedDict((("Position", position), ("Interpolation", interpolation)))
                    for json_param_name, (_, _) in _MP.UniversalGradation.get_params():
                        if json_param_name in zone:
                            univaersal_zone_dict[json_param_name] = zone[json_param_name]
                    return univaersal_zone_dict
                if zone["PosMin"] != zone["PosMax"]:
                    universal_gradation.append(create_universal_zone_dict(zone, zone["PosMin"], "None"))
                if zone["PosMin"] == zone["PosMax"] or\
                    (i < len(max_gradation) - 1 and zone["PosMax"] < max_gradation[i + 1]["PosMin"]): # 連続していない場合
                    universal_gradation.append(create_universal_zone_dict(zone, zone["PosMax"], "SMOOTH"))
            # 拡張機能の名前を重複しないようにする
            advanced_name = mat.name_full + "_Advanced"
            while advanced_name in material_names:
                advanced_name += "_"
            material_names.add(advanced_name)
            a_material_dict[_keyNames.PARAMS]["AdvancedMaterial"] = advanced_name
            # 拡張機能を出力
            a_advanced_dict = OrderedDict()
            materials[advanced_name] = a_advanced_dict
            a_advanced_dict[_keyNames.NODE_NAME] = advanced_name
            a_advanced_dict[_keyNames.NODE_TYPE] = _MP.AdvancedMaterialNode.get_node_to_export_name()
            a_advanced_dict[_keyNames.PARAMS] = OrderedDict()
            self._export_node_params(a_advanced_dict[_keyNames.PARAMS], mat, _MP.AdvancedMaterialNode)
            # ライン関連機能を設定
            if getattr(mat, "pcl4_line_functions", None) is not None:
                a_material_dict[_keyNames.PARAMS]["LineFunctions"] = mat.pcl4_line_functions.name_full
        # ライン関連機能を出力
        for mat, line_functions_node in util.enumerate_material_and_line_functions():
            if mat.name_full not in materials:
                materials[mat.name_full] = \
                    util.create_pencil_material_dummy(mat.name_full, mat.pcl4_line_functions.name_full)
            if mat.pcl4_line_functions.name_full in materials:
                continue
            a_line_functions_dict = OrderedDict()
            materials[mat.pcl4_line_functions.name_full] = a_line_functions_dict
            a_line_functions_dict[_keyNames.NODE_NAME] = mat.pcl4_line_functions.name_full
            a_line_functions_dict[_keyNames.NODE_TYPE] = _MP.MaterialLineFunctionsNode.get_node_to_export_name()
            a_line_functions_dict[_keyNames.PARAMS] = OrderedDict()
            self._export_node_params(a_line_functions_dict[_keyNames.PARAMS], line_functions_node,
                                     _MP.MaterialLineFunctionsNode)
        return materials

    def getattr(self, obj, prop_name, default=None):
        if hasattr(obj, "get_overrided_attr"):
            return obj.get_overrided_attr(prop_name, default=default, context=self.context)
        return getattr(obj, prop_name, default) if default is not None else getattr(obj, prop_name)

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
        curve_points = util.get_curve_points(node, self.getattr(node, prop_name))
        universal_curve = util.make_universal_curve(node, self.getattr(node, prop_name))
        ret = OrderedDict()
        ret[_keyNames.BLENDER_CURVE_KEYS] = curve_points
        ret[_keyNames.UNIVERSAL_CURVE_KEYS] = universal_curve
        return ret

    def _export_object(self, node, prop_name):
        obj = self.getattr(node, prop_name)
        return obj.name if obj is not None else None

    def _export_object_list(self, node, prop_name):
        return [x.content.name for x in self.getattr(node, prop_name) if x.content is not None]

    def _export_string(self, node, prop_name):
        return self.getattr(node, prop_name)

    def _export_int(self, node, prop_name):
        return self.getattr(node, prop_name)

    def _export_float(self, node, prop_name):
        return self.getattr(node, prop_name)

    def _export_float_percentage(self, node, prop_name):
        #  Blender: percentage -> JSON: raw value
        percentage_value = self.getattr(node, prop_name)
        return percentage_value / 100.0

    def _export_float_angle(self, node, prop_name):
        #  Blender: radian -> JSON: degree
        rad_value = self.getattr(node, prop_name)
        return math.degrees(rad_value)

    def _export_float_with_scale(self, node, prop_name):
        return self.getattr(node, prop_name)

    def _export_bool(self, node, prop_name):
        return self.getattr(node, prop_name)

    def _export_bool_list_8(self, node, prop_name):
        return list(self.getattr(node, prop_name, [])) + [False] * (8 - len(list(self.getattr(node, prop_name, []))))

    def _export_enum(self, node, prop_name):
        enum_str = self.getattr(node, prop_name)
        enum_items = node.bl_rna.properties[prop_name].enum_items
        return next(x.value for x in enum_items if x.identifier == enum_str)

    def _export_float_vector_2(self, node, prop_name):
        vector2 = self.getattr(node, prop_name)
        return [vector2.x, vector2.y]

    def _export_color(self, node, prop_name):
        color = self.getattr(node, prop_name)
        srgb_color = util.linear_to_srgb(color[:3])
        return [srgb_color[0], srgb_color[1], srgb_color[2], 1.0]

    def _export_image(self, node, prop_name):
        image = self.getattr(node, prop_name)
        return image.name if image is not None else None

    def _export_gradation(self, node, prop_name):
        pass

    def _export_material(self, node, prop_name):
        return {
            "Name": self.getattr(node, prop_name).name,
            "Id": None,
            "MaterialType": "Other"
        }

    def _export_material_list(self, node, prop_name):
        return [{"Name": x.content.name,
                 "Id": None,
                 "MaterialType": "Other"} for x in self.getattr(node, prop_name) if x.content is not None]

    def _export_advanced_material(self, node, prop_name):
        pass

    def _export_userdef(self, node, prop_name):
        pass

    def _export_float_array_string(self, node, prop_name):
        return [float(x) for x in self.getattr(node, prop_name).split(",")]

    def _export_color_array_string(self, node, prop_name):
        return [util.linear_to_srgb([float(y) for y in x.split(",")][:3]) + [1.0] for x in self.getattr(node, prop_name).split(";")]

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
