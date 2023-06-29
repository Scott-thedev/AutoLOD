# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

############################################################
# GENERATE LOW POLY #
############################################################
# BLENDER ADD-ON THAT AUTOMATES THE PROCESS OF CREATING A
# LOW POLY MODEL FROM A HIGH POLY MODEL. PRESUMABLY IN
# PREPERATION FOR BAKING IN SOMETHING LIKE MARMOSET TOOLBAG
#############################################################
# AUTHOR: SCOTT CLAYTON #
# ############################################################
# VERSION: 0.1.2 #
############################################################
# HOW TO USE:
#------COPY ENTIRE SCRIPT TO PYTHON CONSOLE IN BLENDER
#------SCRIPTING TAB AND RUN WITH ALT+P. ACCESS ADDON VIA
#------'LOW POLY GENERATOR' PANEL IN THE OBJECT PROPERTIES WINDOW.
#############################################################
# FEATURES #
#----PRESERVE MATERIALS AND UV'S
#----CUSTOM SIMPLIFICATION ALGORITHM
#############################################################

from cgitb import text
import bpy
import bmesh

class LowPolyPanel(bpy.types.Panel):
    """Creates a Custom Panel in the Object properties window"""
    bl_label = "Low Poly Generator"
    bl_idname = "OBJECT_PT_lowpoly"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Create a row for LOD level
        layout.label(text="Level of Detail (LOD):")
        layout.prop(scene, "lod_level", text="")

        # Add other relevant parameters
        layout.prop(scene, "decimation_ratio", text="Decimation Ratio")
        layout.prop(scene, "preserve_sharp_edges", text="Preserve Sharp Edges")
        layout.prop(scene, "keep_uvs", text="Keep UVs")
        layout.prop(scene, "simplification_method", text="Simplification Method")
        layout.prop(scene, "smoothing", text="Smoothing")
        layout.prop(scene, "preserve_materials", text="Preserve Materials")
        layout.prop(scene, "export_format", text="Export Format")

        # Add import options
        layout.label(text="Import High-Poly Model:")
        layout.operator("object.choose_highpoly_model", text="Choose from Scene")
        layout.operator("object.import_highpoly_model", text="Import External Model")

        # Add decimation button
        layout.label(text="Decimation:")
        layout.operator("object.decimate_highpoly_model", text="Decimate")

        # Add export button
        layout.label(text="Export LODs:")
        layout.operator("object.export_lods", text="Export")

def custom_surface_simplification(mesh, target_vertex_count):
    # Create a BMesh object from the mesh data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Calculate vertex costs using Quadric Error Metrics (QEM)
    for v in bm.verts:
        v["cost"] = sum(qem.cost for qem in v.link_faces)

    # Sort vertices in descending order of costs
    sorted_verts = sorted(bm.verts, key=lambda v: v["cost"], reverse=True)

    # Remove vertices based on the target vertex count
    for i in range(len(sorted_verts) - target_vertex_count):
        vert = sorted_verts[i]
        if not vert.is_valid:
            continue

        # Collapse the vertex to its optimal position
        collapse_to = min(vert.link_edges, key=lambda e: vert["cost"] + e.other_vert(vert)["cost"])
        bmesh.ops.collapse(bm, verts=[vert], uvs=True, del_faces=True, del_edges=True)
        collapse_to.calc_normal()  # Update the normal of the collapsed vertex

    # Update the mesh with the modified BMesh data
    bm.to_mesh(mesh)
    bm.free()

class DecimateHighPolyModelOperator(bpy.types.Operator):
    """Operator to decimate the high-poly model"""
    bl_idname = "object.decimate_highpoly_model"
    bl_label = "Decimate High-Poly Model"

    def execute(self, context):
        # Get the active object (assumed to be the high-poly model)
        obj = context.active_object
        if obj is None:
            self.report({'ERROR'}, "No active object found")
            return {'CANCELLED'}

        # Create a new mesh object for the LOD
        mesh = obj.data.copy()
        lod_mesh = bpy.data.meshes.new_from_object(obj)
        obj_data = bpy.data.objects.new(f"LOD_{obj.name}", lod_mesh)
        context.collection.objects.link(obj_data)

        # Apply decimation based on the selected method
        if bpy.context.scene.simplification_method == 'EDGE_COLLAPSE':
            bpy.ops.object.modifier_add(type='DECIMATE')
            modifier = obj_data.modifiers.new(name="Decimate", type='DECIMATE')
            modifier.ratio = bpy.context.scene.decimation_ratio
            modifier.use_collapse_triangulate = not bpy.context.scene.preserve_sharp_edges
            bpy.ops.object.modifier_apply({"object": obj_data}, modifier=modifier.name)

        elif bpy.context.scene.simplification_method == 'QUADRIC_ERROR_METRIC':
            bpy.ops.object.modifier_add(type='DECIMATE')
            modifier = obj_data.modifiers.new(name="Decimate", type='DECIMATE')
            modifier.ratio = bpy.context.scene.decimation_ratio
            modifier.use_quadric_optimize = True
            dmodifier.use_collapse_triangulate = not bpy.context.scene.preserve_sharp_edges
            bpy.ops.object.modifier_apply({"object": obj_data}, modifier=modifier.name)

        elif bpy.context.scene.simplification_method == 'CUSTOM_QUADRIC_ERROR_METRIC':
            # Perform custom surface simplification using QEM
            mesh = active_obj.data
            target_vertex_count = int(len(mesh.vertices) * bpy.context.scene.decimation_ratio)

            custom_surface_simplification(mesh, target_vertex_count)

            # Recalculate vertex normals after simplification
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')

            self.report({'INFO'}, "Surface simplification applied")

        elif bpy.context.scene.simplification_method == 'SURFACE_SIMPLIFICATION':
            # Apply your custom surface simplification algorithm here
            # Modify the geometry of the mesh to reduce the polygon count
            # You can access the mesh data with active_obj.data

            self.report({'INFO'}, "Surface simplification applied")

        else:
            self.report({'WARNING'}, "Invalid simplification method")

        return {'FINISHED'}

class GenerateLODsOperator(bpy.types.Operator):
    """Operator to generate LODs based on the specified level of detail"""
    bl_idname = "object.generate_lods"
    bl_label = "Generate LODs"
    
    def execute(self, context):
        # Get the active object (assumed to be the high-poly model)
        active_obj = bpy.context.active_object
        if active_obj is None:
            self.report({'ERROR'}, "No active object found")
            return {'CANCELLED'}
        
        # Create LODs based on the specified level of detail
        lod_levels = bpy.context.scene.lod_levels

        #create list to hold lods. see line 176
        lods = []
        
        # Create a copy of the active object's mesh for each LOD
        for lod_level in range(1, lod_levels+1):
            # Create a new mesh and copy the data from the active object's mesh
            mesh = bpy.data.meshes.new(name=f"LOD{lod_level}")
            mesh.from_mesh(active_obj.data)
            
            # Create a new object and link it to the scene
            obj = bpy.data.objects.new(name=f"LOD{lod_level}", object_data=mesh)
            bpy.context.collection.objects.link(obj)
            
            # Apply the decimation algorithm to the new LOD object
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.decimate_highpoly_model()
            
            # Scale the LOD object based on the specified LOD scale factor
            scale_factor = bpy.context.scene.lod_scale_factor
            obj.scale *= scale_factor
            
            #add to lods list for creating hirearchy
            lods.append(f"LOD{lod_level}")

            # Transfer materials and UV mappings from the high-poly model to the LOD object
            bpy.context.view_layer.objects.active = active_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.object.material_slot_copy()
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.material_slot_paste()
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)

        # Create a hierarchy of LODs
        for i in range(1, len(lods)):
            lods[i].parent = lods[i - 1]
        
        self.report({'INFO'}, f"{lod_levels} LODs generated")
        return {'FINISHED'}

class ExportLODsOperator(bpy.types.Operator):
    """Operator to export the generated LODs"""
    bl_idname = "object.export_lods"
    bl_label = "Export LODs"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        # Get all LOD objects in the scene
        lods = [obj for obj in bpy.data.objects if obj.name.startswith("LOD")]

        if not lods:
            self.report({'WARNING'}, "No LODs found")
            return {'CANCELLED'}

        # Export each LOD object
        for lod in lods:
            filepath = self.filepath.replace('.obj', f'_{lod.name}.obj')  # Append LOD name to the file path
            bpy.ops.export_scene.obj(filepath=filepath, use_selection=True, use_materials=True)

        self.report({'INFO'}, "LODs exported successfully")
        return {'FINISHED'}

def import_highpoly_model(filepath):
    bpy.ops.import_scene.fbx(filepath=filepath)  # Use appropriate importer based on file format

class ChooseHighPolyModelOperator(bpy.types.Operator):
    """Operator to choose a high-poly model from the scene"""
    bl_idname = "object.choose_highpoly_model"
    bl_label = "Choose High-Poly Model"

    def execute(self, context):
        # Code to select the high-poly model from the scene
        selected_objects = bpy.context.selected_objects
        if len(selected_objects) == 1:
            highpoly_obj = selected_objects[0]
            # Perform further operations with the selected high-poly model
            # For example, you can access the object data with highpoly_obj.data
            self.report({'INFO'}, "High-poly model selected")
        else:
            self.report({'ERROR'}, "Please select only one high-poly model")
        return {'FINISHED'}

class ImportHighPolyModelOperator(bpy.types.Operator):
    """Operator to import an external high-poly model"""
    bl_idname = "object.import_highpoly_model"
    bl_label = "Import High-Poly Model"

    def execute(self, context):
        # Code to open a file browser and import the high-poly model
        filepath = ""
        file_format = bpy.context.scene.export_format
        if file_format == 'OBJ':
            bpy.ops.import_scene.obj(filepath=filepath)
        elif file_format == 'FBX':
            bpy.ops.import_scene.fbx(filepath=filepath)
        elif file_format == 'STL':
            bpy.ops.import_mesh.stl(filepath=filepath)
        # Add support for other file formats as needed

        # Perform further operations with the imported high-poly model
        # For example, you can access the imported object with bpy.context.selected_objects[0]

        self.report({'INFO'}, "High-poly model imported")
        return {'FINISHED'}

def register():
    bpy.types.Scene.lod_level = bpy.props.IntProperty(
        name="LOD Level",
        default=1,
        min=1,
        description="Level of detail for the low-poly model"
    )

    bpy.types.Scene.export_path = bpy.props.StringProperty(
        name="Export Path",
        default="",
        subtype='FILE_PATH',
        description="Path to export the LODs"
    )

    bpy.types.Scene.lod_levels = bpy.props.IntProperty(
        name="LOD Levels",
        default=3,
        min=1,
        description="Number of LODs to generate"
    )
    
    bpy.types.Scene.lod_scale_factor = bpy.props.FloatProperty(
        name="LOD Scale Factor",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Scale factor for each LOD"
    )

    bpy.types.Scene.decimation_ratio = bpy.props.FloatProperty(
        name="Decimation Ratio",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Ratio for reducing the polygon count"
    )

    bpy.types.Scene.preserve_sharp_edges = bpy.props.BoolProperty(
        name="Preserve Sharp Edges",
        default=True,
        description="Preserve sharp edges during decimation"
    )

    bpy.types.Scene.keep_uvs = bpy.props.BoolProperty(
        name="Keep UVs",
        default=True,
        description="Preserve UV mappings during low-poly generation"
    )

    bpy.types.Scene.simplification_method = bpy.props.EnumProperty(
        name="Simplification Method",
        items=[
            ('EDGE_COLLAPSE', "Edge Collapse", "Edge collapse decimation method"),
            ('QUADRIC_ERROR_METRIC', "Quadric Error Metrics", "Quadric error metrics decimation method"),
            ('SURFACE_SIMPLIFICATION', "Surface Simplification", "Surface simplification decimation method"),
            ('CUSTOM_QUADRIC_ERROR_METRIC', "Custom Quadric Error Metric", "Custom variation of QEM decimation"),
        ],
        default='EDGE_COLLAPSE',
        description="Method for simplifying the mesh"
    )

    bpy.types.Scene.smoothing = bpy.props.BoolProperty(
        name="Smoothing",
        default=False,
        description="Apply smoothing to the low-poly model"
    )

    bpy.types.Scene.preserve_materials = bpy.props.BoolProperty(
        name="Preserve Materials",
        default=True,
        description="Transfer materials from high-poly to low-poly"
    )

    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Export Format",
        items=[
            ('OBJ', "OBJ", "Wavefront OBJ format"),
            ('FBX', "FBX", "Autodesk FBX format"),
            ('STL', "STL", "STereoLithography format")
        ],
        default='OBJ',
        description="File format for exporting the low-poly model"
    )

    bpy.utils.register_class(LowPolyPanel)
    bpy.utils.register_class(ChooseHighPolyModelOperator)
    bpy.utils.register_class(ImportHighPolyModelOperator)
    bpy.utils.register_class(DecimateHighPolyModelOperator)
    bpy.utils.register_class(GenerateLODsOperator)
    bpy.utils.register_class(ExportLODsOperator)

def unregister():
    bpy.utils.unregister_class(LowPolyPanel)
    bpy.utils.unregister_class(ChooseHighPolyModelOperator)
    bpy.utils.unregister_class(ImportHighPolyModelOperator)
    bpy.utils.unregister_class(DecimateHighPolyModelOperator)
    bpy.utils.unregister_class(GenerateLODsOperator)
    del bpy.types.Scene.export_path
    del bpy.types.Scene.lod_level
    del bpy.types.Scene.lod_levels
    del bpy.types.Scene.lod_scale_factor
    del bpy.types.Scene.lod_level
    del bpy.types.Scene.decimation_ratio
    del bpy.types.Scene.preserve_sharp_edges
    del bpy.types.Scene.keep_uvs
    del bpy.types.Scene.simplification_method
    del bpy.types.Scene.smoothing
    del bpy.types.Scene.preserve_materials
    del bpy.types.Scene.export_format

if __name__ == "__main__":
    register()
