# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from itertools import chain, repeat
from collections import OrderedDict
from . import Settings as settings


def enumerate_all_node_trees():
    if not is_line_addon_installed():
        return ()
    return (x for x in bpy.data.node_groups if x.bl_idname == "Pencil4NodeTreeType")


def enumerate_all_nodes():
    return chain.from_iterable(tree.nodes for tree in enumerate_all_node_trees())


def enumerate_material_and_line_functions():
    if not is_line_addon_installed():
        return
    for mat in bpy.data.materials:
        if mat.pcl4_line_functions is None:
            continue
        node = next((x for x in mat.pcl4_line_functions.node_tree.nodes
                     if x.bl_idname == "Pencil4LineFunctionsContainerNodeType"), None)
        if node is not None:
            yield mat, node


def get_curve_points(node, curve_name):
    curve_node = node.get_curve_data(curve_name)
    if curve_node is None:
        return []
    return [(x.location[0], x.location[1], x.handle_type)
            for x in curve_node.mapping.curves[0].points]


def set_curve_points(node, curve_name, curve_points):
    if len(curve_points) < 2:
        return
    curve_node = node.get_curve_data(curve_name)
    if curve_node is None:
        return
    blender_points = curve_node.mapping.curves[0].points

    for _ in repeat(None, len(blender_points) - 2):
        blender_points.remove(blender_points[0])
    for i, point in enumerate(curve_points):
        if i < 2:
            blender_points[i].location[0] = point[0]
            blender_points[i].location[1] = point[1]
            blender_points[i].handle_type = point[2] if len(point) == 3 else "AUTO"
        else:
            blender_points.new(point[0], point[1])
            blender_points[i].handle_type = point[2] if len(point) == 3 else "AUTO"


def make_universal_curve(node, curve_name):
    return list(zip(
        [x / 8 for x in range(0, 9)],
        node.evaluate_curve(curve_name, 9)))


def create_pencil_material_dummy(node_name, line_functions_id):
    dic = OrderedDict()
    dic["NodeType"] = "PencilMaterial"
    dic["NodeName"] = node_name
    dic["Params"] = {"LineFunctions": line_functions_id}
    return dic


def srgb_to_linear(srgb_array):
    def conv(srgb):
        if srgb <= 0.040448:
            return srgb / 12.92
        else:
            return pow(((srgb + 0.055) / 1.055), 2.4)

    return [conv(x) for x in srgb_array]


def linear_to_srgb(linear_array):
    def conv(linear):
        if linear > 0.003231:
            return 1.055 * (pow(linear, (1 / 2.4))) - 0.055
        else:
            return 12.92 * linear

    return [conv(x) for x in linear_array]


def is_file_version_supported(version):
    try:
        major, minor = (int(x) for x in version.split("."))
        majorMin, minorMin = (int(x) for x in settings.SUPPORTED_FILE_VERSION_MIN.split("."))
        majorMax, minorMax = (int(x) for x in settings.UNSUPPORTED_FILE_VERSION_MIN.split("."))
        return major == majorMin and minorMin <= minor \
               or majorMin < major < majorMax \
               or major == majorMax and minor < minorMax
    except ValueError:
        return False

def operator_call_with_override(op, context, overrides, args={}):
    override = context.copy()
    for k, v in overrides.items():
        override[k] = v
    if hasattr(context, "temp_override"):
        with context.temp_override(**override):
            op('INVOKE_DEFAULT', **args)
    else:
        op(override, 'INVOKE_DEFAULT', **args)

def is_material_addon_installed() -> bool:
    return hasattr(bpy.types.Material, "is_pcl4_material")

def is_line_addon_installed() -> bool:
    return hasattr(bpy.types.Material, "pcl4_line_functions")