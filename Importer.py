# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import json
import math
import inspect
from typing import Iterable

from . import template as _MP
from .template import KeyNames as _keys

from . import Utilities as util


class ImporterSettings:
    line_ids = None
    material_ids = None
    should_overwrite = False
    use_custom_scale = False
    custom_scale_factor = 1.0
    should_import_disabled_brush = True
    should_import_disabled_reduction = True


class Importer:

    def __init__(self):

        # 読み込みを飛ばしたノード
        self.skipped_nodes = {}

        # 読み込みを飛ばしたアトリビュート
        self.skipped_attributes = []

        # スケール
        self.scale_factor = 1.0

        self.importers = {
            _MP.AType.NODE: self._import_node_connection,
            _MP.AType.NODE_LIST: self._import_node_list,
            _MP.AType.CURVE: self._import_curve,
            _MP.AType.OBJECT: self._import_object,
            _MP.AType.OBJECT_LIST: self._import_object_list,
            _MP.AType.STRING: self._import_string,
            _MP.AType.INT: self._import_int,
            _MP.AType.FLOAT: self._import_float,
            _MP.AType.FLOAT_PERCENTAGE: self._import_float_percentage,
            _MP.AType.FLOAT_ANGLE: self._import_float_angle,
            _MP.AType.FLOAT_WITH_SCALE: self._import_float_with_scale,
            _MP.AType.BOOL: self._import_bool,
            _MP.AType.BOOL_LIST_8: self._import_bool_list_8,
            _MP.AType.ENUM: self._import_enum,
            _MP.AType.FLOAT_VECTOR_2: self._import_float_vector_2,
            _MP.AType.COLOR: self._import_color,
            _MP.AType.IMAGE: self._import_image,
            _MP.AType.GRADATION: self._import_gradation,
            _MP.AType.MATERIAL: self._import_material,
            _MP.AType.MATERIAL_LIST: self._import_material_list,
            _MP.AType.ADVANCED_MATERIAL: self._import_advanced_material,
            _MP.AType.USERDEF: self._import_userdef,
            _MP.AType.POSITION_GROUP: self._import_group,
            _MP.AType.COLOR_GROUP: self._import_group,
            _MP.AType.FLOAT_ARRAY: self._import_float_array,
            _MP.AType.FLOAT_ARRAY_STRING: self._import_float_array_string,
            _MP.AType.COLOR_ARRAY_STRING: self._import_color_array_string,
            _MP.AType.NOT_IMPLEMENTED: self._import_not_implemented
        }

        self.node_types = dict((cls.get_node_to_export_name(), cls) for _, cls
                               in inspect.getmembers(_MP, inspect.isclass)
                               if issubclass(cls, _MP.Node) and cls.is_blender_node())

        param_defs = [cls for _, cls
                      in inspect.getmembers(_MP, inspect.isclass)
                      if issubclass(cls, _MP.Node) and cls.is_blender_node()]

        self.export_name_to_blender_id_dict = \
            dict((x.get_node_to_export_name(), x.get_blender_id_name()) for x in param_defs)

        self.node_id_to_node_dict = dict()
        self.imported_materials = dict()
        self.imported_node_trees = dict()

        self.target_node_tree = None
        self.target_scene = None

        self.dummy_advanced_materials = dict()

    def enumerate_lines_and_materials_from_json_file(self, json_file_path):
        """

        :param json_file_path:
        :return:
        """
        try:
            with open(json_file_path) as json_file:
                json_dict = json.load(json_file)
                lines, has_lines = self._try_get(json_dict, _keys.LINES)
                if not has_lines:
                    return ([], [])
                return (self._enumerate_lines_in_json_dict(json_dict),
                        self._enumerate_materials_in_json_dict(json_dict))
        except ValueError:
            return ([], [])
        except OSError:
            return ([], [])

    def import_from_json_file(self, json_file, target_node_tree, target_scene, importer_settings: ImporterSettings):
        """

        :param json_file:
        :param target_node_tree:
        :param target_scene
        :param importer_settings:
        :return:
        """
        try:
            json_dict = json.load(json_file)
        except Exception as e:
            raise ValueError("JSON load failed.")
        return self._import_from_json_dict(json_dict, target_node_tree, target_scene, importer_settings)

    def import_from_json_string(self, json_string, target_node_tree, target_scene, importer_settings: ImporterSettings):
        """

        :param json_string:
        :param target_node_tree:
        :param target_scene
        :param importer_settings:
        :return:
        """
        json_dict = json.loads(json_string)
        return self._import_from_json_dict(json_dict, target_node_tree, target_scene, importer_settings)

    def _import_from_json_dict(self,
                               json_dict,
                               target_node_tree,
                               target_scene,
                               importer_settings: ImporterSettings):
        if not json_dict.keys() >= {_keys.PLATFORM, _keys.FILE_VERSION, _keys.LINES, _keys.MATERIALS}:
            raise ValueError("JSON structure is invalid.")

        if not util.is_file_version_supported(json_dict[_keys.FILE_VERSION]):
            raise ValueError("File version is invalid.")
        
        # 上書きインポートの結果使用されなくなるデータをあとから削除するために、削除対象になり得る使用中のデータを列挙する
        if importer_settings.should_overwrite:
            used_materials = set(mat.pcl4_line_functions for mat, _ in util.enumerate_material_and_line_functions())
            used_node_groups = (x for x in bpy.data.node_groups if x.users > 0)

        # インポート対象のマテリアルIDを列挙
        if importer_settings.material_ids is None:
            material_ids = [x for (x, _) in self._enumerate_materials_in_json_dict(json_dict)]
        else:
            material_ids = importer_settings.material_ids

        # 位置グループ・カラーグループのインポート
        self._create_groups(material_ids, json_dict)

        # マテリアルのインポート
        self._create_pcl4_materials(material_ids, json_dict[_keys.MATERIALS], importer_settings.should_overwrite)

        #  Line Functions Nodeのインポート
        self._create_line_functions(material_ids, json_dict[_keys.MATERIALS])

        # ラインのインポート
        self._import_lines(json_dict, target_node_tree, target_scene, importer_settings)

        # 上書きインポートの結果使用されなくなったデータを削除
        if importer_settings.should_overwrite:
            for material in used_materials:
                if material.users == 0:
                    bpy.data.materials.remove(material)
            for node_group in used_node_groups:
                if node_group.users == 0:
                    bpy.data.node_groups.remove(node_group)


    def _import_lines(self, json_dict, target_node_tree, target_scene, importer_settings: ImporterSettings):
        if target_node_tree is None or not util.is_line_addon_installed():
            return

        for node in target_node_tree.nodes:
            node.select = False

        self.target_node_tree = target_node_tree
        self.target_scene = target_scene
        self._set_scale_factor(json_dict, importer_settings)

        if importer_settings.line_ids is None:
            line_ids = [x for (x, _) in self._enumerate_lines_in_json_dict(json_dict)]
        else:
            line_ids = importer_settings.line_ids

        line_children_ids = self._collect_line_nodes(
            json_dict[_keys.LINES],
            line_ids,
            importer_settings.should_import_disabled_brush,
            importer_settings.should_import_disabled_reduction)

        line_family_ids = line_ids + line_children_ids
        line_family_to_import = {k: v for k, v in json_dict[_keys.LINES].items() if k in line_family_ids}

        if importer_settings.should_overwrite:
            line_node_names = set(n.name for n in target_node_tree.enumerate_lines())
            for node_name in (json_dict[_keys.LINES][line_id][_keys.NODE_NAME] for line_id in line_ids):
                if node_name in line_node_names:
                    target_node_tree.nodes[node_name].delete_if_unused(target_node_tree)
                    line_node_names.remove(node_name)

        #  ラインノードの展開
        node_items, has_node_location = self._create_line_nodes(line_family_to_import, target_node_tree)

        #  ラインノードの接続・パラメータの代入
        self._set_node_parameters(node_items)

        # ノード位置をインポートできていない場合はノードを整列
        if not has_node_location:
            def layout_child_nodes(node):
                for i, intput in enumerate(node.inputs):
                    child = intput.get_connected_node()
                    if child:
                        if node.bl_idname == _MP.LineNode._blenderNodeId:
                            child.location = [
                                node.location[0] + node.new_node_step_x * i + node.new_node_offset_x,
                                node.location[1] + node.new_node_step_y * i + node.new_node_offset_y
                            ]
                        else:
                            child.location = node.calc_new_node_position(i)
                        layout_child_nodes(child)

            new_nodes = set(node for node, _ in node_items.values())
            line_nodes = target_node_tree.enumerate_lines()
            location = [0, 0]
            for i, node in enumerate(line_nodes):
                if not node in new_nodes:
                    location = [node.location[0], node.location[1] + i * 200]
                    break
            for node in line_nodes:
                if node in new_nodes:
                    node.location = location
                    layout_child_nodes(node)
                location = [node.location[0], node.location[1] - 200]
            

    def _set_scale_factor(self, json_dict: dict, importer_settings: ImporterSettings):
        if importer_settings.use_custom_scale:
            self.scale_factor = importer_settings.custom_scale_factor
        else:
            if _keys.SCALE_FACTOR in json_dict and isinstance(json_dict[_keys.SCALE_FACTOR], float):
                self.scale_factor = json_dict[_keys.SCALE_FACTOR]
            else:
                self.scale_factor = 1.0

    @staticmethod
    def _try_get(target, key):
        if not isinstance(target, dict):
            return None, False
        if key not in target:
            return None, False
        return target[key], True

    @staticmethod
    def _enumerate_nodes_in_json_dict(json_dict: dict, nodes_key: str, node_type_name: str) -> list:
        ret = []
        for node_id, node_data in json_dict[nodes_key].items():
            node_type, has_node_type = Importer._try_get(node_data, _keys.NODE_TYPE)
            if not has_node_type or node_type != node_type_name:
                continue
            node_name, has_node_name = Importer._try_get(node_data, _keys.NODE_NAME)
            if not has_node_name or not isinstance(node_name, str):
                continue
            ret.append((node_id, node_name))
        return ret

    @staticmethod
    def _enumerate_lines_in_json_dict(json_dict: dict) -> list:
        return Importer._enumerate_nodes_in_json_dict(
            json_dict,
            _keys.LINES,
            _MP.LineNode.get_node_to_export_name())

    @staticmethod
    def _enumerate_materials_in_json_dict(json_dict: dict) -> list:
        return Importer._enumerate_nodes_in_json_dict(
            json_dict,
            _keys.MATERIALS,
            _MP.PencilMaterialNode.get_node_to_export_name())

    @staticmethod
    def _collect_line_nodes(
            nodes_dict,
            line_ids_to_import,
            should_import_disabled_brush: bool,
            should_import_disabled_reduction: bool):
        whole_node_ids_to_import = set()

        def _add_brush_related_nodes(brush_node_id):
            if not brush_node_id:
                return
            detail_id = nodes_dict[brush_node_id]["Params"]["BrushDetail"]
            whole_node_ids_to_import.add(detail_id)
            color_map_id = nodes_dict[brush_node_id]["Params"]["ColorMap"]
            whole_node_ids_to_import.add(color_map_id)
            size_map_id = nodes_dict[brush_node_id]["Params"]["SizeMap"]
            whole_node_ids_to_import.add(size_map_id)
            brush_map_id = nodes_dict[detail_id]["Params"]["BrushMap"]
            whole_node_ids_to_import.add(brush_map_id)
            distortion_map_id = nodes_dict[detail_id]["Params"]["DistortionMap"]
            whole_node_ids_to_import.add(distortion_map_id)

        for a_line_id in line_ids_to_import:
            # Line -> LineSet
            line_set_ids = nodes_dict[a_line_id]["Params"]["LineSets"]
            for a_line_set_id in line_set_ids:
                whole_node_ids_to_import.add(a_line_set_id)

                # LineSet -> BrushSettings, BrushDetails
                a_line_set_params = nodes_dict[a_line_set_id]["Params"]
                v_brush_id = a_line_set_params["VBrushSettings"]
                whole_node_ids_to_import.add(v_brush_id)
                _add_brush_related_nodes(v_brush_id)
                h_brush_id = a_line_set_params["HBrushSettings"]
                whole_node_ids_to_import.add(h_brush_id)
                _add_brush_related_nodes(h_brush_id)

                # LineSet -> BrushSettings, BrushDetails (Specific)
                specific_brush_settings = [
                    ("VOutline", "VOutlineSpecificOn"),
                    ("VObject", "VObjectSpecificOn"),
                    ("VIntersection", "VIntersectionSpecificOn"),
                    ("VSmooth", "VSmoothSpecificOn"),
                    ("VMaterial", "VMaterialSpecificOn"),
                    ("VSelected", "VSelectedSpecificOn"),
                    ("VNormalAngle", "VNormalAngleSpecificOn"),
                    ("VWireframe", "VWireframeSpecificOn"),
                    ("HOutline", "HOutlineSpecificOn"),
                    ("HObject", "HObjectSpecificOn"),
                    ("HIntersection", "HIntersectionSpecificOn"),
                    ("HSmooth", "HSmoothSpecificOn"),
                    ("HMaterial", "HMaterialSpecificOn"),
                    ("HSelected", "HSelectedSpecificOn"),
                    ("HNormalAngle", "HNormalAngleSpecificOn"),
                    ("HWireframe", "HWireframeSpecificOn")
                ]
                for brush, is_on in specific_brush_settings:
                    if brush not in a_line_set_params or is_on not in a_line_set_params:
                        continue
                    if should_import_disabled_brush or a_line_set_params[is_on]:
                        brush_id = a_line_set_params[brush]
                        whole_node_ids_to_import.add(brush_id)
                        _add_brush_related_nodes(brush_id)

                # LineSet -> ReductionSettings
                specific_reduction_settings = [
                    ("VSizeReduction", "VSizeReductionOn"),
                    ("VAlphaReduction", "VAlphaReductionOn"),
                    ("HSizeReduction", "HSizeReductionOn"),
                    ("HAlphaReduction", "HAlphaReductionOn")
                ]
                for reduction, is_on in specific_reduction_settings:
                    if reduction not in a_line_set_params or is_on not in a_line_set_params:
                        continue
                    if should_import_disabled_reduction or a_line_set_params[is_on]:
                        reduction_id = a_line_set_params[reduction]
                        whole_node_ids_to_import.add(reduction_id)
        #
        if None in whole_node_ids_to_import:
            whole_node_ids_to_import.remove(None)
        return list(whole_node_ids_to_import)

    def _create_line_nodes(self, node_dict, target_node_tree: bpy.types.NodeTree):
        node_items = dict()
        has_node_location = True
        for nid, data in node_dict.items():
            try:
                node_bl_idname = self.export_name_to_blender_id_dict[data[_keys.NODE_TYPE]]
                node_name = data[_keys.NODE_NAME]
                new_node = target_node_tree.nodes.new(type=node_bl_idname)
                new_node.name = node_name
                if _keys.NODE_LOCATION in data:
                    new_node.location = data[_keys.NODE_LOCATION]
                else:
                    has_node_location = False
                node_items[nid] = (new_node, data)
                self.node_id_to_node_dict[nid] = new_node
            except Exception as err:
                self.skipped_nodes[nid] = err
        return node_items, has_node_location

    def _set_node_parameters(self, node_items):
        for nid, (node, data) in node_items.items():
            self._import_parameters_from_json_data(node, nid, data)
            json_params = data[_keys.PARAMS]
            if data[_keys.NODE_TYPE] == "TextureMap" \
                    and "TextureUV" in json_params \
                    and "ExtendedTextureUV" not in json_params:
                self._modify_texture_map_node(node, json_params)

    def _import_parameters_from_json_params(self, object, nid, json_params, params_def):
        for json_param_name, (attr_name, attr_type) in params_def.get_params():
            try:
                self.importers[attr_type](object, attr_name, json_params[json_param_name])
            except Exception as err:
                self.skipped_attributes.append((nid, attr_name, err))

    def _import_parameters_from_json_data(self, object, nid, data):
        self._import_parameters_from_json_params(object, nid, data[_keys.PARAMS], self.node_types[data[_keys.NODE_TYPE]])

    def _create_groups(self, material_ids: Iterable[str], json_dict: dict):
        if not util.is_material_addon_installed():
            return

        material_ids = set(material_ids)
        if len(material_ids) == 0:
            return
        
        material_dict = json_dict[_keys.MATERIALS]
        groups_def = (
            (json_dict.get(_keys.POSITION_GROUP), _MP.PositionGroupNode, "PositionGroup", lambda x: len(x["Positions"]) // 2, bpy.ops.pcl4mtl.new_position_group_node_tree),
            (json_dict.get(_keys.COLOR_GROUP), _MP.ColorGroupNode, "ColorGroup", lambda x: len(x["Colors"]), bpy.ops.pcl4mtl.new_color_group_node_tree),
        )
        for groups_dict, params_def, material_param, num_zones_func, ot_new_group in groups_def:
            if groups_dict is None:
                continue
            group_ids = set()
            for nid, data in material_dict.items():
                if nid not in material_ids:
                    continue
                group_id = data[_keys.PARAMS].get(material_param)
                if group_id is not None:
                    group_ids.add(group_id)
            for nid, data in groups_dict.items():
                try:
                    if nid not in group_ids:
                        continue
                    node_groups_prev = set(bpy.data.node_groups)
                    num_zones = num_zones_func(data[_keys.PARAMS])
                    ot_new_group(num_zones=num_zones)
                    new_group = next((x for x in bpy.data.node_groups if x not in node_groups_prev))
                    self._import_parameters_from_json_params(new_group, nid, data[_keys.PARAMS], params_def)
                    new_group.name = data[_keys.NODE_NAME]
                    self.imported_node_trees[nid] = new_group
                except Exception as err:
                    print(err)
                    self.skipped_nodes[nid] = err

    def _create_pcl4_materials(self, material_ids: Iterable[str], materials_dict: dict, should_overwrite: bool):
        if not util.is_material_addon_installed():
            return

        material_ids = set(material_ids)
        if len(material_ids) == 0:
            return

        class Dummy:
            pass
        class GradationDummy:
            def __init__(self, importer, nid, data) -> None:
                gradation_data = data.get("MaxGradation")
                if gradation_data is None and "UniversalGradation" in data:
                    gradation_data = list()
                    src_data = data["UniversalGradation"]
                    prev = None
                    prev_interpolation = 0
                    for gradation in src_data:
                        curr = Dummy()
                        importer._import_parameters_from_json_params(curr, nid, gradation, _MP.UniversalGradation)
                        position = gradation.get("Position", 0.0)
                        interpolation = gradation.get("Interpolation", 0)
                        if prev is not None and prev_interpolation == 0:
                            gradation_data[-1]["PosMax"] = position
                            if interpolation != 0 and vars(prev) == vars(curr):
                                prev = None
                                continue
                        zone = dict(vars(curr))
                        zone["PosMin"] = position
                        zone["PosMax"] = position
                        gradation_data.append(zone)
                        prev = curr
                        prev_interpolation = interpolation
                    if len(gradation_data) > 0:
                        gradation_data[0]["PosMin"] = 0.0
                        gradation_data[-1]["PosMax"] = 1.0
                if gradation_data is None:
                    self.zone_num = 0
                    return
                params_def = _MP.MaxGradation
                self.zone_num = len(gradation_data)
                dummies = []
                for json_params in gradation_data:
                    dummy = Dummy()
                    dummies.append(dummy)
                    importer._import_parameters_from_json_params(dummy, nid, json_params, params_def)
                attr_defaults = {
                    "pcl4mtl_zone_ids": 1,
                    "pcl4mtl_zone_min_positions": 0.0,
                    "pcl4mtl_zone_max_positions": 0.0,
                    "pcl4mtl_zone_color_ons": True,
                    "pcl4mtl_zone_colors": (0.0, 0.0, 0.0, 1.0),
                    "pcl4mtl_zone_map_opacities": 1.0,
                    "pcl4mtl_zone_map_ons": False,
                    "pcl4mtl_zone_color_amounts": 1.0,
                }
                for _, (attr_name, attr_type) in params_def.get_params():
                    if attr_type == _MP.AType.NOT_IMPLEMENTED:
                        continue
                    value_list = [getattr(dummy, attr_name, attr_defaults[attr_name]) for dummy in dummies]
                    attr = ",".join([str(x) for x in value_list]) if attr_type != _MP.AType.COLOR else\
                        ";".join([",".join([str(x) for x in sub_list]) for sub_list in value_list])
                    setattr(self, attr_name, attr)

        for nid in material_ids:
            data = materials_dict[nid]
            try:
                if data[_keys.NODE_TYPE] != "AdvancedMaterial" or nid in self.dummy_advanced_materials:
                    continue
                dummy = Dummy()
                self.dummy_advanced_materials[nid] = dummy
                self._import_parameters_from_json_data(dummy, nid, data)
            except Exception as err:
                self.skipped_nodes[nid] = err
        for nid in material_ids:
            data = materials_dict[nid]
            try:
                if data[_keys.NODE_TYPE] != "PencilMaterial" or nid not in material_ids:
                    continue
                name = data[_keys.NODE_NAME]
                if should_overwrite and name in bpy.data.materials and bpy.data.materials[name].library is None:
                    material = bpy.data.materials[name]
                else:
                    material = bpy.data.materials.new(name=name)
                    material.name = name
                self.imported_materials[name] = material
                material.use_nodes = True
                dummy = GradationDummy(self, nid, data[_keys.PARAMS].get("Gradation"))
                util.operator_call_with_override(
                    bpy.ops.pcl4mtl.initialize_material,
                    bpy.context, {"material": material}, {"zone_num": dummy.zone_num})
                self._import_parameters_from_json_data(material, nid, data)
                for _, (attr_name, _) in _MP.MaxGradation.get_params():
                    value = getattr(dummy, attr_name, None) if attr_name is not None else None
                    if value is not None:
                        setattr(material, attr_name, value)
            except Exception as err:
                self.skipped_nodes[nid] = err


    def _create_line_functions(self, material_ids: Iterable[str], materials_dict):
        if not util.is_line_addon_installed():
            return
        for nid in material_ids:
            data = materials_dict[nid]
            try:
                if data[_keys.NODE_TYPE] != "PencilMaterial":
                    continue
                line_functions_id = data[_keys.PARAMS]["LineFunctions"]
                if line_functions_id is None or line_functions_id not in materials_dict:
                    continue
                material_name = data[_keys.NODE_NAME]
                target_material = self.imported_materials.get(material_name)
                if target_material is None:
                    target_material = bpy.data.materials.get(material_name)
                    if target_material is None:
                        target_material = bpy.data.materials.new(name=material_name)
                        target_material.name = material_name
                        self.imported_materials[material_name] = target_material
                line_functions_data = materials_dict[line_functions_id]
                line_finctions_name = line_functions_data[_keys.NODE_NAME]
                line_functions_mat = self.imported_materials.get(line_finctions_name)
                if line_functions_mat is None:
                    line_functions_mat = bpy.data.materials.new(name=line_finctions_name)
                    self.imported_materials[line_finctions_name] = line_functions_mat
                    line_functions_mat.use_nodes = True
                    while len(line_functions_mat.node_tree.nodes) > 0:
                        line_functions_mat.node_tree.nodes.remove(line_functions_mat.node_tree.nodes[0])
                    node = line_functions_mat.node_tree.nodes.new(type="Pencil4LineFunctionsContainerNodeType")
                    node.name = line_finctions_name
                    line_functions_mat.use_nodes = False

                    json_params = line_functions_data[_keys.PARAMS]
                    node_params_def = self.node_types["LineRelatedFunctions"]
                    for json_param_name, (attr_name, attr_type) in node_params_def.get_params():
                        try:
                            self.importers[attr_type](node, attr_name, json_params[json_param_name])
                        except Exception as err:
                            self.skipped_attributes.append((nid, attr_name, err))
                target_material.pcl4_line_functions = line_functions_mat
            except Exception as err:
                self.skipped_nodes[nid] = err

    """
    Importers
    """

    def _import_node_connection(self, node, prop_name, value):
        if value not in self.node_id_to_node_dict:
            return
        socket_id = node.bl_rna.properties[prop_name].default
        child_node = self.node_id_to_node_dict[value]
        self.target_node_tree.links.new(node.inputs[node.find_input_socket_index(socket_id)], child_node.outputs[0])

    def _import_node_list(self, node, prop_name, value):
        if len(value) == 0:
            return

        for i, val in enumerate(value):
            if val not in self.node_id_to_node_dict:
                continue
            child_node = self.node_id_to_node_dict[val]
            self.target_node_tree.links.new(node.inputs[i], child_node.outputs[0])

    def _import_curve(self, node, prop_name, value):
        if _keys.BLENDER_CURVE_KEYS in value:
            util.set_curve_points(node, getattr(node, prop_name), value[_keys.BLENDER_CURVE_KEYS])
        elif _keys.UNIVERSAL_CURVE_KEYS in value:
            util.set_curve_points(node, getattr(node, prop_name), value[_keys.UNIVERSAL_CURVE_KEYS])

    def _import_object(self, node, prop_name, value):
        if value is None:
            return
        obj = self.target_scene.objects.get(value)
        if obj is None:
            return
        setattr(node, prop_name, obj)

    def _import_object_list(self, node, prop_name, value):
        for obj_name in value:
            obj = self.target_scene.objects.get(obj_name)
            if obj is not None:
                new_elem = getattr(node, prop_name).add()
                new_elem.content = obj

    def _import_string(self, node, prop_name, value):
        setattr(node, prop_name, value)

    def _import_int(self, node, prop_name, value):
        setattr(node, prop_name, int(value))

    def _import_float(self, node, prop_name, value):
        setattr(node, prop_name, float(value))

    def _import_float_percentage(self, node, prop_name, value):
        #  JSON: raw value -> Blender: percentage
        setattr(node, prop_name, float(value) * 100.0)

    def _import_float_angle(self, node, prop_name, value):
        #  JSON: degree -> Blender: radian
        setattr(node, prop_name, math.radians(float(value)))

    def _import_float_with_scale(self, node, prop_name, value):
        setattr(node, prop_name, float(value) * self.scale_factor)

    def _import_bool(self, node, prop_name, value):
        setattr(node, prop_name, bool(value))

    def _import_bool_list_8(self, node, prop_name, value):
        setattr(node, prop_name, value[:min(8, len(value))] + [False] * max(0, 8 - len(value)))

    def _import_enum(self, node, prop_name, value):
        enum_items = node.bl_rna.properties[prop_name].enum_items
        setattr(node, prop_name, enum_items[value].identifier)

    def _import_float_vector_2(self, node, prop_name, value):
        setattr(node, prop_name, value)

    def _import_color(self, node, prop_name, value):
        setattr(node, prop_name, util.srgb_to_linear(value[0:3]))

    def _import_image(self, node, prop_name, value):
        if value in bpy.data.images:
            setattr(node, prop_name, bpy.data.images[value])

    def _import_gradation(self, node, prop_name, value):
        pass

    def _import_material(self, node, prop_name, value):
        if value is None:
            return
        mat = self.imported_materials.get(value["Name"])
        if mat is None:
            mat = bpy.data.materials.get(value["Name"])
        if mat is None:
            return
        setattr(node, prop_name, mat)

    def _import_material_list(self, node, prop_name, value):
        for mat_data in value:
            mat = self.imported_materials.get(mat_data["Name"])
            if mat is None:
                mat = bpy.data.materials.get(mat_data["Name"])
            if mat is not None:
                new_elem = getattr(node, prop_name).add()
                new_elem.content = mat

    def _import_advanced_material(self, node, prop_name, value):
        dummy = self.dummy_advanced_materials.get(value, None)
        if dummy is None:
            return
        params_def = self.node_types["AdvancedMaterial"]
        for _, (attr_name, _) in params_def.get_params():
            if attr_name is not None and hasattr(dummy, attr_name):
                setattr(node, attr_name, getattr(dummy, attr_name))
    
    def _import_group(self, node, prop_name, value):
        if value in self.imported_node_trees:
            setattr(node, prop_name, self.imported_node_trees[value].name_full)

    def _import_float_array(self, node, prop_name, value):
        setattr(node, prop_name, value)

    def _import_float_array_string(self, node, prop_name, value):
        setattr(node, prop_name, ",".join([str(x) for x in value]))
    
    def _import_color_array_string(self, node, prop_name, value):
        setattr(node, prop_name, ";".join([",".join([str(x) for x in sub_list]) for sub_list in value]))

    def _import_userdef(self, node, prop_name, value):
        pass

    def _import_not_implemented(*_):
        pass

    """
    for Unity
    """
    def _modify_texture_map_node(self, node, data):
        original_texture_uv = data["TextureUV"]
        if original_texture_uv == 0:
            node.uv_source = "SCREEN"
        else:
            node.uv_source = "OBJECTUV"
            node.uv_selection_mode = "INDEX"
            node.uv_index = original_texture_uv - 1
