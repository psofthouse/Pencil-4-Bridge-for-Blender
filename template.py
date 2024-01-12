# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import inspect


class AType:
    NODE = "node"
    NODE_LIST = "nodeList"
    CURVE = "curve"
    OBJECT = "object"
    OBJECT_LIST = "objectList"
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    FLOAT_PERCENTAGE = "floatPercentage"
    FLOAT_ANGLE = "floatAngle"
    FLOAT_WITH_SCALE = "floatWithScale"
    BOOL = "bool"
    BOOL_LIST_8 = "boolList8"
    ENUM = "enum"
    FLOAT_VECTOR_2 = "floatVector2"
    COLOR = "color"
    IMAGE = "image"
    GRADATION = "gradation"
    MATERIAL = "material"
    MATERIAL_LIST = "materialList"
    ADVANCED_MATERIAL = "advancedMaterial"  # Max版との仕様の違いの吸収用
    USERDEF = "userDef"
    POSITION_GROUP = "positionGroup"
    COLOR_GROUP = "colorGroup"
    FLOAT_ARRAY = "floatArray"
    FLOAT_ARRAY_STRING = "floatArrayString"
    COLOR_ARRAY_STRING = "colorArrayString"
    NOT_IMPLEMENTED = "notImplemented"


class KeyNames:
    PLATFORM = "Platform"
    FILE_VERSION = "FileVersion"
    SCALE_FACTOR = "ScaleFactor"
    LINES = "LineNode"
    MATERIALS = "MaterialNode"
    POSITION_GROUP = "PositionGroup"
    COLOR_GROUP = "ColorGroup"
    PENCIL_MATERIAL = "PencilMaterial"
    BLENDER_CURVE_KEYS = "BlenderCurveKeys"
    UNIVERSAL_CURVE_KEYS = "UniversalKeys"
    NODE_NAME = "NodeName"
    NODE_TYPE = "NodeType"
    PARAMS = "Params"
    NODE_LOCATION = "BlenderNodeLocation"


class Node:
    @classmethod
    def get_params(cls):
        return [(x, getattr(cls, x))
                for x in dir(cls)
                if not x.startswith("_") and not inspect.ismethod(getattr(cls, x))]

    @classmethod
    def get_node_to_export_name(cls):
        return getattr(cls, "_nameToExport")

    @classmethod
    def get_blender_node_name(cls):
        return getattr(cls, "_blenderNodeName")

    @classmethod
    def get_blender_id_name(cls):
        return getattr(cls, "_blenderNodeId")

    @classmethod
    def is_blender_node(cls):
        return hasattr(cls, "_blenderNodeName")


class BrushDetailNode(Node):
    _nameToExport = "BrushDetailSettings"
    _blenderNodeName = "BrushDetailNode"
    _blenderNodeId = "Pencil4BrushDetailNodeType"
    BrushType = "brush_type", AType.ENUM
    BrushMapOn = "brush_map_on", AType.BOOL
    BrushMap = "brush_map", AType.NODE
    MapOpacity = "brush_map_opacity", AType.FLOAT
    Stretch = "stretch", AType.FLOAT
    StretchRandom = "stretch_random", AType.FLOAT_PERCENTAGE
    Angle = "angle", AType.FLOAT_ANGLE
    AngleRandom = "angle_random", AType.FLOAT_ANGLE
    Groove = "groove", AType.FLOAT
    GrooveNumber = "groove_number", AType.INT
    Size = "size", AType.FLOAT
    SizeRandom = "size_random", AType.FLOAT_PERCENTAGE
    Antialiasing = "antialiasing", AType.FLOAT
    HorizontalSpace = "horizontal_space", AType.FLOAT
    HorizontalSpaceRandom = "horizontal_space_random", AType.FLOAT_PERCENTAGE
    VerticalSpace = "vertical_space", AType.FLOAT
    VerticalSpaceRandom = "vertical_space_random", AType.FLOAT_PERCENTAGE
    ReductionStart = "reduction_start", AType.FLOAT
    ReductionEnd = "reduction_end", AType.FLOAT

    StrokeType = "stroke_type", AType.ENUM
    LineType = "line_type", AType.ENUM
    Length = "length", AType.FLOAT
    LengthRandom = "length_random", AType.FLOAT_PERCENTAGE
    Space = "space", AType.FLOAT
    SpaceRandom = "space_random", AType.FLOAT_PERCENTAGE
    LengthSizeRandom = None, AType.NOT_IMPLEMENTED
    Extend = "extend", AType.FLOAT
    ExtendRandom = "extend_random", AType.FLOAT_PERCENTAGE
    LineCopy = "line_copy", AType.INT
    LineCopyRandom = "line_copy_random", AType.INT
    NormalOffset = "normal_offset", AType.FLOAT
    NormalOffsetRandom = "normal_offset_random", AType.FLOAT
    XOffset = "x_offset", AType.FLOAT
    XOffsetRandom = "x_offset_random", AType.FLOAT
    YOffset = "y_offset", AType.FLOAT
    YOffsetRandom = "y_offset_random", AType.FLOAT
    LineSplitAngle = "line_split_angle", AType.FLOAT_ANGLE
    MinLineLength = "min_line_length", AType.FLOAT
    LineLinkLength = "line_link_length", AType.FLOAT
    LineDirection = "line_direction", AType.FLOAT_ANGLE
    LoopDirectionType = "loop_direction_type", AType.ENUM

    DistortionEnable = "distortion_enabled", AType.BOOL
    DistortionMapOn = "distortion_map_on", AType.BOOL
    DistortionMap = "distortion_map", AType.NODE
    DistortionMapAmount = "distortion_map_amount", AType.FLOAT
    DistortionAmount = "distortion_amount", AType.FLOAT
    DistortionRandom = "distortion_random", AType.FLOAT_PERCENTAGE
    DistortionCycles = "distortion_cycles", AType.FLOAT
    DistortionCyclesRandom = "distortion_cycles_random", AType.FLOAT_PERCENTAGE
    DistortionPhase = "distortion_phase", AType.FLOAT_ANGLE
    DistortionPhaseRandom = "distortion_phase_random", AType.FLOAT

    SizeReductionEnable = "size_reduction_enabled", AType.BOOL
    SizeReductionCurve = "size_reduction_curve", AType.CURVE

    AlphaReductionEnable = "alpha_reduction_enabled", AType.BOOL
    AlphaReductionCurve = "alpha_reduction_curve", AType.CURVE

    ColorSpaceType = "color_space_type", AType.ENUM
    ColorRed = "color_space_red", AType.FLOAT
    ColorGreen = "color_space_green", AType.FLOAT
    ColorBlue = "color_space_blue", AType.FLOAT


class BrushSettingsNode(Node):
    _nameToExport = "BrushSettings"
    _blenderNodeName = "BrushSettingsNode"
    _blenderNodeId = "Pencil4BrushSettingsNodeType"
    BrushDetail = "brush_detail_node", AType.NODE
    BlendMode = None, AType.NOT_IMPLEMENTED
    BlendAmount = "blend_amount", AType.FLOAT
    BrushColor = "brush_color", AType.COLOR
    ColorMapOn = "color_map_on", AType.BOOL
    ColorMap = "color_map", AType.NODE
    ColorMapOpacity = "color_map_opacity", AType.FLOAT
    Size = "size", AType.FLOAT
    SizeMapOn = "size_map_on", AType.BOOL
    SizeMap = "size_map", AType.NODE
    SizeMapAmount = "size_map_amount", AType.FLOAT


class LineNode(Node):
    _nameToExport = "Line"
    _blenderNodeName = "LineNode"
    _blenderNodeId = "Pencil4LineNodeType"
    Active = "is_active", AType.BOOL
    LineSets = "line_sets", AType.NODE_LIST
    RenderPriority = "render_priority", AType.INT
    LineSizeType = "line_size_type", AType.ENUM
    OutputRenderElementsOnly = "is_output_to_render_elements_only", AType.BOOL
    OverSampling = "over_sampling", AType.INT
    Antialiasing = "antialiasing", AType.FLOAT
    OffscreenDistance = "off_screen_distance", AType.FLOAT
    RandomSeed = "random_seed", AType.INT


class LineSetNode(Node):
    _nameToExport = "LineSet"
    _blenderNodeName = "LineSetNode"
    _blenderNodeId = "Pencil4LineSetNodeType"
    On = "is_on", AType.BOOL
    Id = "lineset_id", AType.INT
    WeldsEdges = "is_weld_edges", AType.BOOL
    MaskHiddenLines = "is_mask_hidden_lines", AType.BOOL
    UserDef = None, AType.USERDEF
    Objects = "objects", AType.OBJECT_LIST
    Materials = "materials", AType.MATERIAL_LIST
    VBrushSettings = "v_brush_settings", AType.NODE
    VOutlineOn = "v_outline_on", AType.BOOL
    VOutlineOpen = "v_outline_open", AType.BOOL
    VOutlineMergeGroups = "v_outline_merge_groups", AType.BOOL
    VOutlineSpecificOn = "v_outline_specific_on", AType.BOOL
    VOutline = "v_outline_brush_settings", AType.NODE
    VObjectOn = "v_object_on", AType.BOOL
    VObjectOpen = "v_object_open", AType.BOOL
    VObjectSpecificOn = "v_object_specific_on", AType.BOOL
    VObject = "v_object_brush_settings", AType.NODE
    VIntersectionOn = "v_intersection_on", AType.BOOL
    VIntersectionSelf = "v_intersection_self", AType.BOOL
    VIntersectionSpecificOn = "v_intersection_specific_on", AType.BOOL
    VIntersection = "v_intersection_brush_settings", AType.NODE
    VSmoothOn = "v_smooth_on", AType.BOOL
    VSmoothSpecificOn = "v_smooth_specific_on", AType.BOOL
    VSmooth = "v_smooth_brush_settings", AType.NODE
    VMaterialOn = "v_material_on", AType.BOOL
    VMaterialSpecificOn = "v_material_specific_on", AType.BOOL
    VMaterial = "v_material_brush_settings", AType.NODE
    VSelectedOn = "v_selected_on", AType.BOOL
    VSelectedSpecificOn = "v_selected_specific_on", AType.BOOL
    VSelected = "v_selected_brush_settings", AType.NODE
    VNormalAngleOn = "v_normal_angle_on", AType.BOOL
    VNormalAngleSpecificOn = "v_normal_angle_specific_on", AType.BOOL
    VNormalAngle = "v_normal_angle_brush_settings", AType.NODE
    VNormalAngleMin = "v_normal_angle_min", AType.FLOAT_ANGLE
    VNormalAngleMax = "v_normal_angle_max", AType.FLOAT_ANGLE
    VWireframeOn = "v_wireframe_on", AType.BOOL
    VWireframeSpecificOn = "v_wireframe_specific_on", AType.BOOL
    VWireframe = "v_wireframe_brush_settings", AType.NODE
    VSizeReductionOn = "v_size_reduction_on", AType.BOOL
    VSizeReduction = "v_size_reduction_settings", AType.NODE
    VAlphaReductionOn = "v_alpha_reduction_on", AType.BOOL
    VAlphaReduction = "v_alpha_reduction_settings", AType.NODE
    HBrushSettings = "h_brush_settings", AType.NODE
    HOutlineOn = "h_outline_on", AType.BOOL
    HOutlineOpen = "h_outline_open", AType.BOOL
    HOutlineMergeGroups = "h_outline_merge_groups", AType.BOOL
    HOutlineSpecificOn = "h_outline_specific_on", AType.BOOL
    HOutline = "h_outline_brush_settings", AType.NODE
    HObjectOn = "h_object_on", AType.BOOL
    HObjectOpen = "h_object_open", AType.BOOL
    HObjectSpecificOn = "h_object_specific_on", AType.BOOL
    HObject = "h_object_brush_settings", AType.NODE
    HIntersectionOn = "h_intersection_on", AType.BOOL
    HIntersectionSelf = "h_intersection_self", AType.BOOL
    HIntersectionSpecificOn = "h_intersection_specific_on", AType.BOOL
    HIntersection = "h_intersection_brush_settings", AType.NODE
    HSmoothOn = "h_smooth_on", AType.BOOL
    HSmoothSpecificOn = "h_smooth_specific_on", AType.BOOL
    HSmooth = "h_smooth_brush_settings", AType.NODE
    HMaterialOn = "h_material_on", AType.BOOL
    HMaterialSpecificOn = "h_material_specific_on", AType.BOOL
    HMaterial = "h_material_brush_settings", AType.NODE
    HSelectedOn = "h_selected_on", AType.BOOL
    HSelectedSpecificOn = "h_selected_specific_on", AType.BOOL
    HSelected = "h_selected_brush_settings", AType.NODE
    HNormalAngleOn = "h_normal_angle_on", AType.BOOL
    HNormalAngleSpecificOn = "h_normal_angle_specific_on", AType.BOOL
    HNormalAngle = "h_normal_angle_brush_settings", AType.NODE
    HNormalAngleMin = "h_normal_angle_min", AType.FLOAT_ANGLE
    HNormalAngleMax = "h_normal_angle_max", AType.FLOAT_ANGLE
    HWireframeOn = "h_wireframe_on", AType.BOOL
    HWireframeSpecificOn = "h_wireframe_specific_on", AType.BOOL
    HWireframe = "h_wireframe_brush_settings", AType.NODE
    HSizeReductionOn = "h_size_reduction_on", AType.BOOL
    HSizeReduction = "h_size_reduction_settings", AType.NODE
    HAlphaReductionOn = "h_alpha_reduction_on", AType.BOOL
    HAlphaReduction = "h_alpha_reduction_settings", AType.NODE


class MaterialLineFunctionsNode(Node):
    _nameToExport = "LineRelatedFunctions"
    _blenderNodeName = "LineFunctionsContainerNode"
    _blenderNodeId = "Pencil4LineFunctionsContainerNodeType"
    ReplaceOutlineOn = "outline_on", AType.BOOL
    ReplaceOutlineColor = "outline_color", AType.COLOR
    ReplaceOutlineAmount = "outline_amount", AType.FLOAT
    ReplaceObjectOn = "object_on", AType.BOOL
    ReplaceObjectColor = "object_color", AType.COLOR
    ReplaceObjectAmount = "object_amount", AType.FLOAT
    ReplaceIntersectionOn = "intersection_on", AType.BOOL
    ReplaceIntersectionColor = "intersection_color", AType.COLOR
    ReplaceIntersectionAmount = "intersection_amount", AType.FLOAT
    ReplaceSmoothOn = "smooth_on", AType.BOOL
    ReplaceSmoothColor = "smooth_color", AType.COLOR
    ReplaceSmoothAmount = "smooth_amount", AType.FLOAT
    ReplaceMaterialOn = "material_on", AType.BOOL
    ReplaceMaterialColor = "material_color", AType.COLOR
    ReplaceMaterialAmount = "material_amount", AType.FLOAT
    ReplaceSelectedOn = "selected_edge_on", AType.BOOL
    ReplaceSelectedColor = "selected_edge_color", AType.COLOR
    ReplaceSelectedAmount = "selected_edge_amount", AType.FLOAT
    ReplaceNormalAngleOn = "normal_angle_on", AType.BOOL
    ReplaceNormalAngleColor = "normal_angle_color", AType.COLOR
    ReplaceNormalAngleAmount = "normal_angle_amount", AType.FLOAT
    ReplaceWireframeOn = "wireframe_on", AType.BOOL
    ReplaceWireframeColor = "wireframe_color", AType.COLOR
    ReplaceWireframeAmount = "wireframe_amount", AType.FLOAT
    DisableIntersection = "disable_intersection", AType.BOOL
    DrawHiddenLines = "draw_hidden_lines", AType.BOOL
    DrawHiddenLinesOfTarget = "draw_hidden_lines_of_targets", AType.BOOL
    DrawObjects = "draw_hidden_lines_of_targets_objects", AType.OBJECT_LIST
    DrawMaterials = "draw_hidden_lines_of_targets_materials", AType.MATERIAL_LIST
    MaskHiddenLinesOfTarget = "mask_hidden_lines_of_targets", AType.BOOL
    MaskObjects = "mask_hidden_lines_of_targets_objects", AType.OBJECT_LIST
    MaskMaterials = "mask_hidden_lines_of_targets_materials", AType.MATERIAL_LIST


class ReductionSettingsNode(Node):
    _nameToExport = "ReductionSettings"
    _blenderNodeName = "ReductionSettingsNode"
    _blenderNodeId = "Pencil4ReductionSettingsNodeType"
    ReductionStart = "reduction_start", AType.FLOAT_WITH_SCALE
    ReductionEnd = "reduction_end", AType.FLOAT_WITH_SCALE
    ReferObject = "refer_object_on", AType.BOOL
    Object = "object_reference", AType.OBJECT
    Curve = "curve", AType.CURVE


class TextureMapNode(Node):
    _nameToExport = "TextureMap"
    _blenderNodeName = "TextureMapNode"
    _blenderNodeId = "Pencil4TextureMapNodeType"
    HoldingTexture = "image", AType.IMAGE
    WrapModeU = "wrap_mode_u", AType.ENUM
    WrapModeV = "wrap_mode_v", AType.ENUM
    FilterMode = "filter_mode", AType.ENUM
    ExtendedTextureUV = "uv_source", AType.ENUM
    Tiling = "tiling", AType.FLOAT_VECTOR_2
    Offset = "offset", AType.FLOAT_VECTOR_2
    
    SourceType = "source_type", AType.ENUM
    UVSelectionMode = "uv_selection_mode", AType.ENUM
    UVIndex = "uv_index", AType.INT
    UVName = "uv_name", AType.STRING
    ObjectColorSelectionMode = "object_color_selection_mode", AType.ENUM
    ObjectColorIndex = "object_color_index", AType.INT
    ObjectColorName = "object_color_name", AType.STRING



class PencilMaterialNode(Node):
    _nameToExport = "PencilMaterial"
    _blenderNodeName = ""
    _blenderNodeId = ""
    AdvancedMaterial = None, AType.ADVANCED_MATERIAL
    BlendMode = "pcl4mtl_highlight_blend", AType.ENUM
    BlendAmount = "pcl4mtl_highlight_amount", AType.FLOAT
    HighlightColor = "pcl4mtl_highlight_color", AType.COLOR
    ColorMapOn = None, AType.NOT_IMPLEMENTED
    ColorMap = None, AType.NOT_IMPLEMENTED
    MapOpacity = None, AType.NOT_IMPLEMENTED
    SpecularLevel = "pcl4mtl_highlight_level", AType.FLOAT
    Glossiness = "pcl4mtl_highlight_glossiness", AType.FLOAT
    Anisotropic = None, AType.NOT_IMPLEMENTED
    Orientation = None, AType.NOT_IMPLEMENTED
    Sharpness = "pcl4mtl_highlight_sharpness", AType.FLOAT
    Squash = None, AType.NOT_IMPLEMENTED
    DiffractionEffect = None, AType.NOT_IMPLEMENTED
    Range = None, AType.NOT_IMPLEMENTED
    PositionGroup = "pcl4mtl_position_group", AType.POSITION_GROUP
    ColorGroup = "pcl4mtl_color_group", AType.COLOR_GROUP


class AdvancedMaterialNode(Node):
    _nameToExport = "AdvancedMaterial"
    _blenderNodeName = ""
    _blenderNodeId = ""
    GradOffsetEnable = "pcl4mtl_grad_offset_on", AType.BOOL
    GradOffsetAmount = "pcl4mtl_grad_offset_amount", AType.FLOAT
    GradOffsetMap = None, AType.NOT_IMPLEMENTED
    GradOffsetMapOffset = "pcl4mtl_grad_offset_offset", AType.FLOAT
    SblendEnable = None, AType.NOT_IMPLEMENTED
    SblendColor = None, AType.NOT_IMPLEMENTED
    SblendMapOpacity = None, AType.NOT_IMPLEMENTED
    SblendMapEnable = None, AType.NOT_IMPLEMENTED
    SblendMap = None, AType.NOT_IMPLEMENTED
    SblendMode = None, AType.NOT_IMPLEMENTED
    SblendAmount = None, AType.NOT_IMPLEMENTED
    LightColEnable = "pcl4mtl_grad_light_color_on", AType.BOOL
    LightColBlend = None, AType.NOT_IMPLEMENTED
    LightcolAmount = "pcl4mtl_grad_light_color_amount", AType.FLOAT
    LightcolZoneIDs = "pcl4mtl_grad_light_color_ids", AType.BOOL_LIST_8
    LightColRelpaceEnable = "pcl4mtl_grad_light_color_replace_on", AType.BOOL
    LightColRelpaceColor = "pcl4mtl_grad_light_color_replace", AType.COLOR
    LightColReplaceAmount = "pcl4mtl_grad_light_color_replace_amount", AType.FLOAT
    HiDesignEnable = None, AType.NOT_IMPLEMENTED
    HiDesignAmount = None, AType.NOT_IMPLEMENTED
    HiDesignAngle = None, AType.NOT_IMPLEMENTED
    ZoneAntiIntensity = None, AType.NOT_IMPLEMENTED
    ZoneAntiEnable = None, AType.NOT_IMPLEMENTED
    SpecificLightsEnable = None, AType.NOT_IMPLEMENTED
    SpecificLightsStrength = None, AType.NOT_IMPLEMENTED
    SpecificTranspEnable = None, AType.NOT_IMPLEMENTED
    SpecificTranspMaterials = None, AType.NOT_IMPLEMENTED
    SpecificTranspMaterialsValue = None, AType.NOT_IMPLEMENTED
    SpecificTranspMapEnable = None, AType.NOT_IMPLEMENTED
    SpecificTranspMapAmount = None, AType.NOT_IMPLEMENTED
    PolygonCntl = None, AType.NOT_IMPLEMENTED


class MaxGradation(Node):
    ZoneId = 'pcl4mtl_zone_ids', AType.INT
    PosMin = 'pcl4mtl_zone_min_positions', AType.FLOAT
    PosMax = 'pcl4mtl_zone_max_positions', AType.FLOAT
    Enable = 'pcl4mtl_zone_color_ons', AType.BOOL
    Color = 'pcl4mtl_zone_colors', AType.COLOR
    MapOpacity = None, AType.NOT_IMPLEMENTED #'pcl4mtl_zone_map_opacities', AType.FLOAT
    ColorMap = None, AType.NOT_IMPLEMENTED
    ColorMapOn = None, AType.NOT_IMPLEMENTED #'pcl4mtl_zone_map_ons', AType.BOOL
    BlendMode = None, AType.NOT_IMPLEMENTED
    BlendAmount = 'pcl4mtl_zone_color_amounts', AType.FLOAT
    StrokeEnable = None, AType.NOT_IMPLEMENTED
    Stroke = None, AType.NOT_IMPLEMENTED


class UniversalGradation(Node):
    Position = None, AType.NOT_IMPLEMENTED
    Interpolation = None, AType.NOT_IMPLEMENTED
    Color = "Color", AType.FLOAT_ARRAY
    Enable = "Enable", AType.BOOL
    BlendMode = None, AType.NOT_IMPLEMENTED
    BlendAmount = "BlendAmount", AType.FLOAT
    ColorMapOn = None, AType.NOT_IMPLEMENTED
    ColorMap = None, AType.NOT_IMPLEMENTED
    MapOpacity = None, AType.NOT_IMPLEMENTED


class PositionGroupNode(Node):
    _nameToExport = "PositionGroup"
    _blenderNodeName = ""
    _blenderNodeId = ""
    Positions = "pcl4_position_group_values", AType.FLOAT_ARRAY_STRING


class ColorGroupNode(Node):
    _nameToExport = "ColorGroup"
    _blenderNodeName = ""
    _blenderNodeId = ""
    Colors = "pcl4_color_group_values", AType.COLOR_ARRAY_STRING
