# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "yuk format",
    "author": "yukizini",
    "version": (2, 3, 1),
    "blender": (2, 93, 0),
    "location": "File > Import-Export",
    "description": "Import-Export yuk",
    "warning": "",
    "doc_url": "https://www.github.com/yukitheclown",
    "category": "Import-Export",
}

if "bpy" in locals():
    if "export_yuk2" in locals():
        importlib.reload(export_yuk2)

import bpy
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper,
        axis_conversion,
        path_reference_mode,
        )



class YUK2Include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_yuk"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "exportMesh")
        layout.prop(operator, "exportAnim")
        layout.prop(operator, "exportCollision")


class Exportyuk(bpy.types.Operator, ExportHelper):
    """Export selection to Extensible 3D file (.yuk)"""
    bl_idname = "export_scene.yuk"
    bl_label = 'Export yuk'
    bl_options = {'PRESET'}

    filename_ext = ".yuk"

    exportMesh: BoolProperty(
            name="Export mesh",
            description="Export Mesh only",
            default=True,
            )
    exportAnim: BoolProperty(
            name="Export Animation",
            description="Export current animation",
            default=False,
            )
    exportCollision: BoolProperty(
            name="Export Collision mesh",
            description="Export collison mesh",
            default=False,
            )


    def execute(self, context):
        from . import export_yuk2

        from mathutils import Matrix

        keywords = self.as_keywords(ignore=("filename_ext", "check_existing" ))

        keywords["globalMatrix"] = axis_conversion(to_forward='-Z', to_up='Y').to_4x4()

        return export_yuk2.Export(self, context, **keywords)

    def draw(self, context):
        pass



def menu_func_export(self, context):
    self.layout.operator(Exportyuk.bl_idname,
                         text="yuk (.yuk)")


classes = (
    Exportyuk,
    YUK2Include,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
