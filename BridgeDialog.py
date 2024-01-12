# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper
from . import Utilities
from .Exporter import Exporter
from .Importer import Importer, ImporterSettings
from . import Translation

NODE_TREE_TYPE_NAME = "Pencil4NodeTreeType"
LINE_EDITOR_MENU_NAME = "PCL4_MT_LineEditorMenu"
current_filepath = ""

class ImportItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    is_import: bpy.props.BoolProperty()
    id: bpy.props.StringProperty()


class PCL4BRIDGE_UL_LineListView(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.alignment = "LEFT"
        row.label(text=" ")
        row2 = row.row()
        row2.alignment = "CENTER"
        row2.prop(item, "is_import", text="")
        row.prop(item, "name", text="", emboss=False, translate=False)

class PCL4BRIDGE_OT_NewLineNodeTree(bpy.types.Operator):
    bl_label = "New Line Node Tree"
    bl_idname = "pcl4bridge.new_line_node_tree"
    bl_options = {"REGISTER", "UNDO"}
    bl_translation_context = Translation.ctxt

    @classmethod
    def poll(cls, context):
        return Utilities.is_line_addon_installed()

    def execute(self, context):
        tree = bpy.data.node_groups.new("Pencil+ 4 Line Node Tree", NODE_TREE_TYPE_NAME)
        context.window_manager.pcl4bridge_target_node_tree = tree
        return {"FINISHED"}


class PCL4BRIDGE_OT_ShowImportDialogOperator(bpy.types.Operator, ImportHelper):
    bl_label = "Import"
    bl_idname = "pcl4bridge.show_import_dialog"
    bl_options = {"REGISTER", "UNDO"}
    bl_translation_context = Translation.ctxt

    filename_ext = ".json"

    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )

    import_mode_items = (
        ("REPLACE", "Replace", "Replace", 0),
        ("MERGE", "Merge", "Merge", 1)
    )

    import_mode: bpy.props.EnumProperty(items=import_mode_items, default="REPLACE")
    is_unit_conversion_auto: bpy.props.BoolProperty(default=True)
    scale_factor: bpy.props.FloatProperty(default=1.0)
    import_lines: bpy.props.BoolProperty(default=True)
    line_list: bpy.props.CollectionProperty(type=ImportItem)
    line_list_selected_index: bpy.props.IntProperty()
    import_materials: bpy.props.BoolProperty(default=True)
    material_list: bpy.props.CollectionProperty(type=ImportItem)
    material_list_selected_index: bpy.props.IntProperty()
    is_import_disabled_specific_brush_settings: bpy.props.BoolProperty(default=False)
    is_import_disabled_reduction_settings: bpy.props.BoolProperty(default=False)

    def __del__(self):
        global current_filepath
        current_filepath = ""

    def check(self, context):
        # ここでself.filepathを読み取る事により、ファイルダイアログ上で選択されたファイルのパスが分かる。
        # 不意に大量に呼ばれることがあるので、選択状態をキャッシュする
        global current_filepath
        if current_filepath != self.filepath:
            current_filepath = self.filepath
            importer = Importer()
            lines, materials = importer.enumerate_lines_and_materials_from_json_file(current_filepath)
            for list_prop, json_items in ((self.line_list, lines), (self.material_list, materials)):
                list_prop.clear()
                for json_id, json_name in json_items:
                    new_item = list_prop.add()
                    new_item.name = json_name
                    new_item.id = json_id
                    new_item.is_import = True

    def cancel(self, context):
        context.window_manager.pcl4bridge_target_node_tree = None

    def execute(self, context):
        settings = ImporterSettings()
        settings.line_ids = []
        settings.material_ids = []
        for enable, src_list, dst_list in ((self.import_lines and Utilities.is_line_addon_installed(), self.line_list, settings.line_ids),
                                           (self.import_materials, self.material_list, settings.material_ids)):
            if enable:
                for item in src_list:
                    if item.is_import:
                        dst_list.append(item.id)
        settings.should_overwrite = self.import_mode == "REPLACE"
        settings.use_custom_scale = not self.is_unit_conversion_auto
        settings.custom_scale_factor = self.scale_factor
        settings.should_import_disabled_brush = self.is_import_disabled_specific_brush_settings
        settings.should_import_disabled_reduction = self.is_import_disabled_reduction_settings

        importer = Importer()
        try:
            with open(self.filepath, mode="r") as f:
                importer.import_from_json_file(f, context.window_manager.pcl4bridge_target_node_tree, context.scene, settings)
        except ValueError as e:
            self.report({"ERROR"}, f"Pencil+ 4 Bridge: {e.args[0]}")

        context.window_manager.pcl4bridge_target_node_tree = None
        return {"FINISHED"}
    
    def invoke(self, context, event):
        if context.space_data.edit_tree is not None and context.space_data.edit_tree.bl_idname == NODE_TREE_TYPE_NAME:
            context.window_manager.pcl4bridge_target_node_tree = context.space_data.edit_tree
        else:
            context.window_manager.pcl4bridge_target_node_tree = next((x for x in bpy.data.node_groups if x.bl_idname == NODE_TREE_TYPE_NAME), None)
        return super().invoke(context, event)

    def draw(self, context):
        pass

    def register():
        bpy.types.WindowManager.pcl4bridge_target_node_tree = bpy.props.PointerProperty(
            type=bpy.types.NodeTree, poll=lambda self, obj: obj.bl_idname == NODE_TREE_TYPE_NAME)

    def unregister():
        del bpy.types.WindowManager.pcl4bridge_target_node_tree


class PCL4BRIDGE_PT_ImportMixin:
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_parent_id = "FILE_PT_operator"
    bl_translation_context = Translation.ctxt

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "PCL4BRIDGE_OT_show_import_dialog"

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        self.draw_impl(operator, context)

    def draw_impl(self, operator, context):
        pass

class PCL4BRIDGE_PT_ImportOptions(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportOptions"
    bl_label = "Options"
    bl_order = 0

    def draw_impl(self, operator, _):
        layout = self.layout
        layout.prop(operator, "import_mode", expand=True)

class PCL4BRIDGE_PT_ImportUnitConversion(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportUnitConversion"
    bl_label = "Unit Conversion"
    bl_order = 1

    def draw_impl(self, operator, _):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(operator, "is_unit_conversion_auto", text="Auto", text_ctxt=Translation.ctxt)
        layout.prop(operator, "scale_factor", text="Scale Factor", text_ctxt=Translation.ctxt)

class PCL4BRIDGE_PT_ImportMaterials(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportMaterials"
    bl_label = ""
    bl_order = 2
    bl_translation_context = Translation.ctxt

    def draw_header(self, context):
        self.layout.prop(context.space_data.active_operator,
                         "import_materials",
                         text="Pencil+ 4 Materials" if Utilities.is_material_addon_installed() else "Materials (Line Functions)",
                         text_ctxt=Translation.ctxt)

    def draw_impl(self, operator, _):
        layout = self.layout
        layout.enabled = operator.import_materials
        layout.template_list(
            "PCL4BRIDGE_UL_LineListView", "materials",
            operator, "material_list",
            operator, "material_list_selected_index"
        )

class PCL4BRIDGE_PT_ImportLines(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportLines"
    bl_label = "Pencil+ 4 Lines"
    bl_order = 3
    bl_translation_context = Translation.ctxt

    def draw_header(self, context):
        self.layout.enabled = Utilities.is_line_addon_installed()
        self.layout.prop(context.space_data.active_operator,
                         "import_lines",
                         text="")

    def draw_impl(self, operator, context):
        layout = self.layout
        layout.use_property_split = True
        layout.enabled = operator.import_lines and Utilities.is_line_addon_installed()
        layout.label(text="Import Destination", text_ctxt=Translation.ctxt)
        layout.template_ID(bpy.context.window_manager, "pcl4bridge_target_node_tree", new="pcl4bridge.new_line_node_tree")
        layout.separator()
        col = layout.column()
        col.enabled = bpy.context.window_manager.pcl4bridge_target_node_tree is not None
        col.template_list(
            "PCL4BRIDGE_UL_LineListView", "lines",
            operator, "line_list",
            operator, "line_list_selected_index"
        )

class PCL4BRIDGE_PT_ImportOthers(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportOthers"
    bl_label = ""
    bl_options = {'HIDE_HEADER'}
    bl_order = 4

    def draw_impl(self, operator, _):
        layout = self.layout
        layout.prop(operator,
                    "is_import_disabled_specific_brush_settings",
                    text="Import disabled Specific Brush Settings",
                    text_ctxt=Translation.ctxt)
        layout.prop(operator,
                    "is_import_disabled_reduction_settings",
                    text="Import disabled Reduction Settings",
                    text_ctxt=Translation.ctxt)


class PCL4BRIDGE_OT_ShowExportDialogOperator(bpy.types.Operator, ExportHelper):
    bl_label = "Export"
    bl_idname = "pcl4bridge.show_export_dialog"
    bl_options = {"REGISTER", "UNDO"}
    bl_translation_context = Translation.ctxt

    filename_ext = ".json"

    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )

    def execute(self, context):
        exporter = Exporter()
        json_str = exporter.export_to_json_string(context)
        with open(self.filepath, mode="w") as f:
            f.write(json_str)
        return {"FINISHED"}


class BridgeMenuMixin:
    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        tree = context.space_data.edit_tree

        row = layout.row()
        row.operator(PCL4BRIDGE_OT_ShowImportDialogOperator.bl_idname, text="Import", text_ctxt=Translation.ctxt)

        row = layout.row()
        row.operator(PCL4BRIDGE_OT_ShowExportDialogOperator.bl_idname, text="Export", text_ctxt=Translation.ctxt)

    @classmethod
    def register(cls):
        cls.unregister()
        if hasattr(bpy.types, cls.target_menu_idname):
            cls.original_menu_fn = getattr(bpy.types, cls.target_menu_idname).draw
            getattr(bpy.types, cls.target_menu_idname).draw = cls.menu_fn

    @classmethod
    def unregister(cls):
        if cls.original_menu_fn is not None:
            if hasattr(bpy.types, cls.target_menu_idname):
                getattr(bpy.types, cls.target_menu_idname).draw = cls.original_menu_fn
            cls.original_menu_fn = None

    @classmethod
    def _poll(cls, context) -> bool:
        pass

    @classmethod
    def _menu_fn(cls, self, context):
        if cls._poll(context):
            if cls.original_menu_fn:
                cls.original_menu_fn(self, context)
            layout = self.layout
            layout.separator()
            layout.menu(cls.bl_idname)


class BridgeMenu(bpy.types.Menu, BridgeMenuMixin):
    bl_label = "Bridge"
    bl_idname = "PCL4BRIDGE_MT_BridgeMenu"
    original_menu_fn = None
    target_menu_idname = LINE_EDITOR_MENU_NAME

    @staticmethod
    def execute_register():
        BridgeMenu.register()

    @staticmethod
    def execute_unregister():
        BridgeMenu.unregister()

    @classmethod
    def _poll(cls, context) -> bool:
        return context.area.ui_type == NODE_TREE_TYPE_NAME
    
    def menu_fn(self, context):
        BridgeMenu._menu_fn(self, context)


class MaterialBridgeMenu(bpy.types.Menu, BridgeMenuMixin):
    bl_label = "Bridge"
    bl_idname = "PCL4BRIDGE_MT_MaterialBridgeMenu"
    original_menu_fn = None
    target_menu_idname = "PCL4MTL_MT_Shader"

    @staticmethod
    def execute_register():
        MaterialBridgeMenu.register()

    @staticmethod
    def execute_unregister():
        MaterialBridgeMenu.unregister()

    @classmethod
    def _poll(cls, context) -> bool:
        return context.space_data.tree_type == 'ShaderNodeTree'
    
    def menu_fn(self, context):
        MaterialBridgeMenu._menu_fn(self, context)

