bl_info = {
	"name": "Yuk2 format",
	"author": "yukizini",
	"version": (0, 0, 0),
	"blender": (2, 74, 0),
	"location": "File > Export, Scene properties",
	"description": "Export yuk2",
	"wiki_url": "http://github.com/yukizini",
	"category": "Export",
}

if "bpy" in locals():
	import imp
	if "export_yuk2" in locals():
		imp.reload(export_yuk2)

import bpy
from bpy.props import (BoolProperty)
from bpy_extras.io_utils import ( ExportHelper, path_reference_mode, axis_conversion )

class ExportYUK2(bpy.types.Operator, ExportHelper):

	"""Save a yuk2 File"""

	bl_idname = "export_scene.yuk2"
	bl_label = 'Export yuk2'
	bl_options = {'PRESET'}

	filename_ext = ".yuk2"

	exportAnim = BoolProperty(name="Export selected objects active animation?", default = True)
	exportMesh = BoolProperty(name="Export selectced mesh?", default = True)

	def execute(self, context):

		from . import export_yuk2

		from mathutils import Matrix
		keywords = self.as_keywords(ignore=("filename_ext", "check_existing" ))

		keywords["globalMatrix"] = axis_conversion(to_forward='-Z', to_up='Y').to_4x4()

		return export_yuk2.Export(self, context, **keywords)

def menu_func_export(self, context):
	self.layout.operator(ExportYUK2.bl_idname, "Export yuk2 (.yuk2)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
	register()
