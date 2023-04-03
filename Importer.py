# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
import json
import math
import inspect

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
            _MP.AType.ENUM: self._import_enum,
            _MP.AType.FLOAT_VECTOR_2: self._import_float_vector_2,
            _MP.AType.COLOR: self._import_color,
            _MP.AType.IMAGE: self._import_image,
            _MP.AType.GRADATION: self._import_gradation,
            _MP.AType.MATERIAL: self._import_material,
            _MP.AType.MATERIAL_LIST: self._import_material_list,
            _MP.AType.ADVANCED_MATERIAL: self._import_advanced_material,
            _MP.AType.USERDEF: self._import_userdef,
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

        self.target_node_tree = None
        self.target_scene = None

    def enumerate_lines_from_json_file(self, json_file_path):
        """

        :param json_file_path:
        :return:
        """
        try:
            with open(json_file_path) as json_file:
                json_dict = json.load(json_file)
                lines, has_lines = self._try_get(json_dict, _keys.LINES)
                if not has_lines:
                    return []
                return self._enumerate_lines_in_json_dict(json_dict)
        except ValueError:
            return []
        except OSError:
            return []

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

        #  Line Functions Nodeのインポート
        self._create_line_functions(json_dict[_keys.MATERIALS])

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
    def _enumerate_lines_in_json_dict(json_dict: dict):
        ret = []
        for node_id, node_data in json_dict[_keys.LINES].items():
            node_type, has_node_type = Importer._try_get(node_data, _keys.NODE_TYPE)
            if not has_node_type:
                continue
            line_node_type_name = _MP.LineNode.get_node_to_export_name()
            if node_type != line_node_type_name:
                continue
            node_name, has_node_name = Importer._try_get(node_data, _keys.NODE_NAME)
            if not has_node_name or not isinstance(node_name, str):
                continue
            ret.append((node_id, node_name))
        return ret

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
            json_params = data[_keys.PARAMS]
            exported_name = data[_keys.NODE_TYPE]
            node_params_def = self.node_types[exported_name]
            for json_param_name, (attr_name, attr_type) in node_params_def.get_params():
                try:
                    self.importers[attr_type](node, attr_name, json_params[json_param_name])
                except Exception as err:
                    self.skipped_attributes.append((nid, attr_name, err))
            if exported_name == "TextureMap":
                print(json_params)
            if exported_name == "TextureMap" \
                    and "TextureUV" in json_params \
                    and "ExtendedTextureUV" not in json_params:
                self._modify_texture_map_node(node, json_params)



    def _create_line_functions(self, materials_dict):
        for nid, data in materials_dict.items():
            try:
                if data[_keys.NODE_TYPE] != "PencilMaterial":
                    continue
                material_name = data[_keys.NODE_NAME]
                line_functions_id = data[_keys.PARAMS]["LineFunctions"]
                if line_functions_id is None:
                    continue
                if line_functions_id not in materials_dict:
                    continue
                line_functions_data = materials_dict[line_functions_id]
                target_material = bpy.data.materials.get(material_name)
                if target_material is None:
                    target_material = bpy.data.materials.new(name=material_name)
                line_functions_mat = bpy.data.materials.new(name=line_functions_data[_keys.NODE_NAME])
                target_material.pcl4_line_functions = line_functions_mat
                line_functions_mat.use_nodes = True
                while len(line_functions_mat.node_tree.nodes) > 0:
                    line_functions_mat.node_tree.nodes.remove(line_functions_mat.node_tree.nodes[0])
                node = line_functions_mat.node_tree.nodes.new(type="Pencil4LineFunctionsContainerNodeType")
                node.name = line_functions_data[_keys.NODE_NAME]
                line_functions_mat.use_nodes = False

                json_params = line_functions_data[_keys.PARAMS]
                node_params_def = self.node_types["LineRelatedFunctions"]
                for json_param_name, (attr_name, attr_type) in node_params_def.get_params():
                    try:
                        self.importers[attr_type](node, attr_name, json_params[json_param_name])
                    except Exception as err:
                        self.skipped_attributes.append((nid, attr_name, err))
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
        mat = bpy.data.materials.get(value["Name"])
        if mat is None:
            return
        setattr(node, prop_name, mat)

    def _import_material_list(self, node, prop_name, value):
        for mat_data in value:
            mat = bpy.data.materials.get(mat_data["Name"])
            if mat is not None:
                new_elem = getattr(node, prop_name).add()
                new_elem.content = mat

    def _import_advanced_material(self, node, prop_name, value):
        pass

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
