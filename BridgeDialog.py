# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper
from .Exporter import Exporter
from .Importer import Importer, ImporterSettings
from . import Translation

NODE_TREE_TYPE_NAME = "Pencil4NodeTreeType"
LINE_EDITOR_MENU_NAME = "PCL4_MT_LineEditorMenu"
current_filepath = ""
original_menu_fn = None

class ImportLineItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    is_import: bpy.props.BoolProperty()
    line_id: bpy.props.StringProperty()


class PCL4BRIDGE_UL_LineListView(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.alignment = "LEFT"
        row.label(text=" ")
        row2 = row.row()
        row2.alignment = "CENTER"
        row2.prop(item, "is_import", text="")
        row.prop(item, "name", text="", emboss=False, translate=False)


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
    line_list: bpy.props.CollectionProperty(type=ImportLineItem)
    line_list_selected_index: bpy.props.IntProperty()
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
            self.line_list.clear()
            importer = Importer()
            lines = importer.enumerate_lines_from_json_file(current_filepath)
            for line_id, line_name in lines:
                new_line = self.line_list.add()
                new_line.name = line_name
                new_line.line_id = line_id
                new_line.is_import = True


    def execute(self, context):
        settings = ImporterSettings()
        settings.line_ids = []
        for line in self.line_list:
            if line.is_import:
                settings.line_ids.append(line.line_id)
        settings.should_overwrite = self.import_mode == "REPLACE"
        settings.use_custom_scale = not self.is_unit_conversion_auto
        settings.custom_scale_factor = self.scale_factor
        settings.should_import_disabled_brush = self.is_import_disabled_specific_brush_settings
        settings.should_import_disabled_reduction = self.is_import_disabled_reduction_settings

        importer = Importer()
        try:
            with open(self.filepath, mode="r") as f:
                importer.import_from_json_file(f, context.space_data.edit_tree, context.scene, settings)
        except ValueError as e:
            self.report({"ERROR"}, f"Pencil+ 4 Bridge: {e.args[0]}")

        return {"FINISHED"}

    def draw(self, context):
        pass


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

        self.draw_impl(operator)

    def draw_impl(self, operator):
        pass

class PCL4BRIDGE_PT_ImportOptions(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportOptions"
    bl_label = "Options"
    bl_order = 0

    def draw_impl(self, operator):
        layout = self.layout
        layout.prop(operator, "import_mode", expand=True)

class PCL4BRIDGE_PT_ImportUnitConversion(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportUnitConversion"
    bl_label = "Unit Conversion"
    bl_order = 1

    def draw_impl(self, operator):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(operator, "is_unit_conversion_auto", text="Auto", text_ctxt=Translation.ctxt)
        layout.prop(operator, "scale_factor", text="Scale Factor", text_ctxt=Translation.ctxt)

class PCL4BRIDGE_PT_ImportLines(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportLines"
    bl_label = "Pencil+ 4 Lines"
    bl_order = 2

    def draw_impl(self, operator):
        layout = self.layout
        layout.template_list(
            "PCL4BRIDGE_UL_LineListView", "",
            operator, "line_list",
            operator, "line_list_selected_index"
        )

class PCL4BRIDGE_PT_ImportOthers(bpy.types.Panel, PCL4BRIDGE_PT_ImportMixin):
    bl_idname = "PCL4BRIDGE_PT_ImportOthers"
    bl_label = ""
    bl_options = {'HIDE_HEADER'}
    bl_order = 3

    def draw_impl(self, operator):
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
        json_str = exporter.export_to_json_string()
        with open(self.filepath, mode="w") as f:
            f.write(json_str)
        return {"FINISHED"}


class BridgeMenu(bpy.types.Menu):
    bl_label = "Bridge"
    bl_idname = "PCL4BRIDGE_MT_BridgeMenu"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        tree = context.space_data.edit_tree

        row = layout.row()
        row.operator(PCL4BRIDGE_OT_ShowImportDialogOperator.bl_idname, text="Import", text_ctxt=Translation.ctxt)
        row.enabled = tree.is_entity()

        row = layout.row()
        row.operator(PCL4BRIDGE_OT_ShowExportDialogOperator.bl_idname, text="Export", text_ctxt=Translation.ctxt)

    @staticmethod
    def execute_register():
        register()

    @staticmethod
    def execute_unregister():
        unregister()


def menu_fn(self, context):
    if context.area.ui_type == NODE_TREE_TYPE_NAME:
        global original_menu_fn
        if original_menu_fn:
            original_menu_fn(self, context)
        layout = self.layout
        layout.separator()
        layout.menu(BridgeMenu.bl_idname)


def register():
    if hasattr(bpy.types, LINE_EDITOR_MENU_NAME):
        global original_menu_fn
        original_menu_fn = bpy.types.PCL4_MT_LineEditorMenu.draw
        bpy.types.PCL4_MT_LineEditorMenu.draw = menu_fn


def unregister():
    if hasattr(bpy.types, LINE_EDITOR_MENU_NAME):
        global original_menu_fn
        bpy.types.PCL4_MT_LineEditorMenu.draw = original_menu_fn
        original_menu_fn = None


