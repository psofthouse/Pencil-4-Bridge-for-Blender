# SPDX-License-Identifier: GPL-2.0-or-later
# The Original Code is Copyright (C) P SOFTHOUSE Co., Ltd. All rights reserved.

bl_info = {
    "name": "PSOFT Pencil+ 4 Bridge",
    "author": "P SOFTHOUSE",
    "description": "Transfer Pencil+ 4 Line settings between Blender and 3ds Max, Maya and Unity [469f4d4b]",
    "blender": (3, 0, 0),
    "version": (4, 0, 0),
    "location": "",
    "warning": "",
    "category": "Import-Export"
}

import bpy
from . import Translation
from . import auto_load
auto_load.init()


def register():
    bpy.app.translations.register(__name__, Translation.translation_dict)
    auto_load.register()


def unregister():
    auto_load.unregister()
    bpy.app.translations.unregister(__name__)


if __name__ == "__main__":
    register()
