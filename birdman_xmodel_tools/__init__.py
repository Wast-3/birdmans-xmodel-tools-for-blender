import bpy
import bmesh
from .PyCoD import xmodel

#faces need to be triangulated

bl_info = {
    "name": "Birdman's xmodel tools for Blender",
    "blender": (2, 80, 0),
    "version": (1,0),
    "category": "Export",
    "description": "Enables the exporting of xmodels from blender. Currently does not support bones or animations.",
    "doc_url": ""
    }
    
def register():
    class_registration()

def unregister():
    class_unregister()

def class_registration():
    class_list = (ExportSettingProperties, XModelExportPanel, ExportMeshOperator)
    for i in class_list:
        bpy.utils.register_class(i)
    
    bpy.types.Scene.xmodel_settings = bpy.props.PointerProperty(type=ExportSettingProperties)
    
def class_unregister():
    class_list = (ExportSettingProperties, XModelExportPanel, ExportMeshOperator)
    for i in reversed(class_list):
        bpy.utils.unregister_class(i)
    del bpy.types.Scene.xmodel_settings
    
                                                        
class ExportSettingProperties(bpy.types.PropertyGroup):
    select_version_dropdown: bpy.props.EnumProperty(
                                    items=(
                                            ("7", "XModel Version 7", "XModel Version 7"),
                                            ("6", "XModel Version 6", "XModel Version 6"),
                                            ("5", "XModel Version 5", "XModel Version 6")
                                        ),
                                    name="XModelVersionSelection",
                                    default="7",
                                    description="Target Version"
                                )
    select_output_dir_dropdown: bpy.props.StringProperty(
                                                    name="birdman_xmodel_output_dir",
                                                    description="Set the output directory where the xmodel outputs will be stored",
                                                    subtype="DIR_PATH"
                                                )
    select_toggle_invert_normals: bpy.props.BoolProperty(name="birdman_xmodel_toggle_invert_normals", description="Invert Normals?")
    
    auto_triangulate_mesh: bpy.props.BoolProperty(name="birdman_xmodel_toggle_auto_triangulate", description="Auto Triangulate Mesh?")
    
    
class ExportMeshOperator(bpy.types.Operator):
    bl_idname = "birdman.export_mesh"
    bl_label = "Export selected mesh to xmodel"
    
    def execute(self, context):
        print("getting ready to export model...")
        version = bpy.context.scene.xmodel_settings.select_version_dropdown
        dir = bpy.context.scene.xmodel_settings.select_output_dir_dropdown
        invert_normals = bpy.context.scene.xmodel_settings.select_toggle_invert_normals
        triangulate_mesh = bpy.context.scene.xmodel_settings.auto_triangulate_mesh
        export_xmodel(dir, invert_normals, version, triangulate_mesh)
        
        return {'FINISHED'}
        

class XModelExportPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_xmodel_export"
    bl_label = "Export object to xModel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"

    def draw(self, context):
        xmodel_settings = context.scene.xmodel_settings
        
        self.layout.label(text="Exports the selected model to xmodel format")
        self.layout.label(text="Note: This addon is still in development.")
        self.layout.label(text="Unsupported features: Bones, multiple materials, multiple meshes")
        
        options_box = self.layout.box()
        options_box.label(text="Options:")
        options_box.prop(xmodel_settings, "select_version_dropdown", text="xModel Version")
        options_box.prop(xmodel_settings, "select_output_dir_dropdown", text="Output Directory")
        options_box.label(text="Normals may need to be inverted for mesh to properly export")
        options_box.prop(xmodel_settings, "select_toggle_invert_normals", text="Invert Normals?")
        options_box.label(text="XModel meshes are triangular-faced only. Auto triangulate mesh?")
        options_box.prop(xmodel_settings, "auto_triangulate_mesh", text="Auto Triangulate Mesh?")
        self.layout.operator("birdman.export_mesh")
        
        
    def draw_header(self, context):
        pass
        
def export_xmodel(output_dir, flip_normals=True, xmodel_version=7, auto_triangulate=True):
    mesh = get_selected_mesh()
    current_object = bpy.context.selected_objects[0]
    
    #print_verts(mesh)
    #print_tris(mesh)
    print_uvmap(mesh)
    
    if flip_normals is True:
        bpy.context.view_layer.objects.active = current_object
        
        print("Flipping normals for exported mesh")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')
    
    #Triangulate Mesh
    if auto_triangulate is True:
        bpy.context.view_layer.objects.active = current_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
        bpy.ops.object.mode_set(mode='OBJECT')
    
    #Create xmodel object
    xmodel_model = xmodel.Model()

    #Create fake bone for xmodel
    #Note that xmodel supports multiple bones, but for now we do not support that
    xmodel_model.bones.append(fake_bone())
    
    #Create xmodel mesh
    xmodel_mesh_name = mesh.name
    xmodel_mesh = xmodel.Mesh(xmodel_mesh_name)
    
    #Write verts in order with default "fake" bone and weight.
    xmodel_mesh = xmodel_add_verts(mesh, xmodel_mesh)
    
    #We need to write out the faces now. 
    xmodel_mesh = xmodel_add_faces(mesh, xmodel_mesh)
    
    #Add base material
    
    xmodel_model = xmodel_add_materials(mesh, xmodel_model)
    
    xmodel_model.meshes.append(xmodel_mesh)
    
    
    #outputs
    output_name = output_dir + f"{mesh.name}"
    
    xmodel_version = int(xmodel_version)
    
    print(output_name)
    
    xmodel_model.WriteFile_Raw(output_name + ".xmodel_export", xmodel_version)
    xmodel_model.WriteFile_Bin(output_name + ".xmodel_bin", xmodel_version)
    
    if flip_normals is True:
        print("UnFlipping normals for exported mesh")
        
        bpy.context.view_layer.objects.active = current_object
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')

def xmodel_add_materials(mesh, xmodel_model):
    #Only supports one material for now, not sure how xmodel format supports multiple materials. 
    #Get material name from mesh
    
    if not mesh.materials:
        raise Exception("Mesh does not have a material assigned. Please assign a material to this mesh before exporting")
    
    material_name = mesh.materials[0].name
    
    #Create material object
    #name, type, images
    #images look a bit weird, not exactly sure how to make this. It doesn't seem to matter once in APE anyways.
    xmodel_image_dict = {"color_map": f"{material_name}.tif"} 
    
    xmodel_material = xmodel.Material(material_name, "Lambert", xmodel_image_dict)
    
    xmodel_model.materials.append(xmodel_material)
    
    return(xmodel_model)
    

def xmodel_add_faces(mesh, xmodel_mesh):
    #Assuming model is made of triangles.
    #Keep in mind polygon = face.
    for polygon in mesh.polygons:
        #Create face object for this polygon.
        xmodel_face = xmodel.Face(0,0)
        
        i = 0
        
        if len(polygon.vertices) > 3:
            raise Exception("More than 3 verts in face. Please triangulate mesh")
            print(f"A face failed to be converted. The polygon count is above 3 polygon count: {len(polygon.vertices)}")
        
        print(f"Polygon {polygon}")
        for loop_index in polygon.loop_indices:
            
            vert_index = mesh.loops[loop_index].vertex_index
            
            #Both the UV loop and vert should refer to the same vert index...

            #Get actual vert
            vert = mesh.vertices[vert_index]
            
            #Get vert coords. Shouldn't be needed though.
            vertco = vert.co
             
            #Get vert normal
            vertnormal = vert.normal
            
            #Now we need to grab the uv data from the loops.
            
            #use the loop index to grab relevant UV data.
            current_uvmap = mesh.uv_layers.active
            print(f"Current loop index is {loop_index}. Current Vert Index is {vert_index}")
            uv_coords = current_uvmap.data[loop_index].uv
            
            print(f"Retrieved UV Coords Are {uv_coords}")
            
            #We are going to ignore getting vert colors for now.
            
            #Prepare the data for xmodel
            xmodel_vertnormal = (vert.normal[0], vert.normal[1], vert.normal[2])
            
            #For whatever reason, it appears that we need to invert the U coordinate. This is just how xmodel is. This was an 8 hour troubleshooting process. Kill me.
            xmodel_uv_coords = (uv_coords.x, (1 - uv_coords.y))
            
            #Create a dummy color object.
            #RGBA
            xmodel_vertcolor = (0,0,0,1)
            
            #Create an xmodel face vert object
            xmodel_facevert = xmodel.FaceVertex(vert_index, color=xmodel_vertcolor, normal=xmodel_vertnormal, uv=xmodel_uv_coords)
            
            #Trying to fix a UV mapping bug...
            
            face_order = [0, 2, 1]
            
            xmodel_face.indices[face_order[i]] = xmodel_facevert

            #xmodel_face.indices[i] = xmodel_facevert
            
            i = i+1
                
            
        
        xmodel_mesh.faces.append(xmodel_face)
    return(xmodel_mesh)
            
def xmodel_add_verts(mesh, xmodel_mesh):
    #this order SHOULD be global and constant...
    for vert in mesh.vertices:
        vert_co = (vert.co[0], vert.co[1], vert.co[2])
        print(f"debug: vert.co converted to touple: {vert_co}")
        
        #Create xmodel vertex
        xmodel_vertex = xmodel.Vertex(vert_co)
        
        #Append default weight to default "fake" bone
        xmodel_vertex.weights.append((0, 1.0))
        
        #Append xmodel vert object to overall xmodel mesh
        xmodel_mesh.verts.append(xmodel_vertex)
    return(xmodel_mesh)
        
def fake_bone():
    fake_bone = xmodel.Bone("TAG_ORIGIN", -1)
    fake_bone.offset = (0,0,0)
    fake_bone.matrix = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]
    return fake_bone

#It seems like xmodel only supports one uvmapping so we should just grab the active one.
def print_uvmap(mesh):
    uvmap = mesh.uv_layers.active
    #Alright this is where things get a bit confusing. We need to iterate over the polygons in our mesh.
    #The indice of each polygon's (face) loops. A loop references a single vertex and edge.
    #It looks like the indice of the loop will match the vert indice.
    for polygon in mesh.polygons:
        #This SHOULD match the verts correctly
        for loop in polygon.loop_indices:
            print("UV: " + str(uvmap.data[loop].uv))

#Polygons are faces. In this case we expect triangular polygons as this is what the xmodel format requires.
def print_tris(mesh):
    for polygon in mesh.polygons:
        print(polygon)
        #Here we can see that blender is saving our asses. The verts here ALREADY reference by index, which means we can match them to the already written verts by index. Whew.
        for vert in polygon.vertices:
            print(vert)

def print_verts(mesh):
    for vert in mesh.vertices:
        print(vert.co)
    
def get_selected_mesh():
    if len(bpy.context.selected_objects) == 0:
        print("Select a mesh")
        raise Exception("MESH NOT SELECTED")
        return("error")
    if len(bpy.context.selected_objects) > 1 or 0:
        print("More than one object is selected currently. Please select a single mesh")
        raise Exception("TOO MANY MESHES SELECTED")
        return("error")
    #print(bpy.context.selected_objects)
    target_object = bpy.context.selected_objects[0]
    target_mesh = target_object.data
    return(target_mesh)

if __name__ == "__main__":
    register()