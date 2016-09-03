bl_info = {
    "name": "image_layers",
    "author": "ywaby",
    "version": (0, 0, 1),
    "blender": (2, 77),
    "description": "image with layers manager"
                         "support psd file",
    "warning": "",
    "wiki_url": "http://github.com"
                "Scripts/Add_Mesh/Planes_from_Images",
    "tracker_url": "http://github.com", 
    "support": "TESTING",
    "category": "system"
}

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator
from bpy.props import (
            StringProperty,
            BoolProperty,
            EnumProperty,
            IntProperty,
            FloatProperty,
            CollectionProperty,
            BoolVectorProperty,
            PointerProperty
            )
import os
from  bl_tree_view import UI_TreeView
from  psd_tools import PSDImage
from  psd_tools.user_api import bl_support
from psd_tools.user_api.utils import BBox

###### utils ##########   
def get_layers_from_image(image, only_visible = True):
    """layers = image.layers_data.layers, get type = layer only"""
    layers = image.layers_data.layers
    if not only_visible:
        result_layers = [layer for layer in layers if layer == "LAYER"]
    else :
        result_layers =[]
        idx = 0
        while(idx < len(layers)) :
            layer = layers[idx]            
            if layer.type == "GROUP_START":
                if layer.is_visible == False:
                    idx = UI_TreeView.get_group_end(layers, idx)
            elif layer.type == "LAYER":      
                if layer.is_visible == True:
                    result_layers.append(layer)
            idx += 1
    return result_layers

def get_layers_from_group(image, group_idx, only_visible =True):
    layers = image.layers_data.layers
    end_idx = UI_TreeView.get_group_end(layers, group_idx)
    if not only_visible:
        result_layers = [layer for layer in layers[group_idx:end_idx] if layer == "LAYER"]
    else :
        result_layers =[]
        idx = group_idx
        while(idx < end_idx) :
            layer = layers[idx]            
            if layer.type == "GROUP_START":
                if layer.is_visible == False:
                    idx = UI_TreeView.get_group_end(layers, idx)
            elif layer.type == "LAYER":      
                if layer.is_visible == True:
                    result_layers.append(layer)
            idx += 1
    return result_layers

###### import #####

def btn_import_layers_image(self, context):
    self.layout.operator(ImportLayersImage.bl_idname, text="Layers Image")

class ImportLayersImage(Operator, ImportHelper):
    """Impot layers image (psd)"""
    bl_idname = "import.layers_image"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Image With Layers"

    filter_glob = StringProperty(
            default="*.psd",
            options={'HIDDEN'},
            maxlen=255,  # Max internal buffer length, longer would be clamped.
            )

    def execute(self, context):
        import time
        start_CPU = time.clock()
        import_layers_image(context, self.filepath)
        end_CPU = time.clock()
        self.report({'INFO'}, "%f"%(end_CPU-start_CPU)) #info window
        return {'FINISHED'}


def get_layers_from_psd(decoded_data, psd_layers, layers_data):
    #psd data to bl image layer
    for layer in psd_layers: 
        if layer.is_group:     
                lm_layer =  layers_data.layers.add()
                lm_layer.type = "GROUP_START"       
                lm_layer.is_visible = layer.visible
                lm_layer.name = layer.name   
                lm_layer.group_down = not layer.closed     
                get_layers_from_psd(decoded_data, layer.layers,  layers_data)
                lm_layer =  layers_data.layers.add()
                lm_layer.type = "GROUP_END"
        else :
            # layer is layer data
            header = decoded_data.header  
            lm_layer =  layers_data.layers.add()
            lm_layer.type = "LAYER"   
            lm_layer.is_visible = layer.visible
            lm_layer.name = layer.name  
            #bl_bbox = psd_bbox_to_bl(layer.bbox, header.height)
            #lm_layer["position"] = [bl_bbox.x1, bl_bbox.y1, bl_bbox.x2, bl_bbox.y2]
            bbox = layer.bbox
            lm_layer["position"] = bl_support.psd_xy_to_bl(header.height, bbox.x1, bbox.y1, bbox.x2, bbox.y2 )
            layers_rd = decoded_data.layer_and_mask_data.layers
            layer_rd = layers_rd.layer_records[layer._index]   
            lm_layer["pixels"] = bl_support.channels_to_bl_pixels(
                channels = layers_rd.channel_image_data[layer._index],
                channel_ids = bl_support._get_layer_channel_ids(layer_rd),
                width = layer_rd.width(),
                height = layer_rd.height(),
                depth = header.depth,
                target_has_alpha = True
            )
    return 

def import_layers_image(context, filepath):
    psd = PSDImage.load(filepath)   
    name = os.path.basename(filepath)
    image = bpy.data.images.new(name, psd.header.width, psd.header.height, alpha = True )
    get_layers_from_psd(psd.decoded_data, psd.layers, image.layers_data )
    update_image(image)
    return image

###### layer manager #########    

def update_image(image):
    layers = get_layers_from_image(image)
    #filter layer
    layers = [layer for layer in layers 
                        if  layer["position"][3] -  layer["position"][1] > 0 or layer["position"][2] -  layer["position"][0]  > 0 ]   
    base_bbox = BBox(0,0,image.size[0],image.size[1])
    base_pixels = [0.0, 0.0, 0.0, 0.0]*image.size[0]*image.size[1]
    #image.generated_color =  [0.0, 0.0, 0.0, 0.0]
    for layer in reversed(layers): 
        layer_bbox = BBox(layer["position"][0], layer["position"][1], layer["position"][2], layer["position"][3])
        bl_support.layer_nor_mix(layer["pixels"], layer_bbox, base_pixels, base_bbox )
    image.pixels = base_pixels


class LayerVisible(bpy.types.Operator):
    """Show/hide  layer (alt to show only)"""
    bl_idname =  "image.layer_visible"
    bl_label = "Show/Hide Layer"
    bl_options = {'REGISTER', 'UNDO'} 
    layer_idx = IntProperty(default = -1)
    has_alt = BoolProperty(options={'SKIP_SAVE'})
    visible = EnumProperty(
            name="visible Set",
            description="",
            items=(('ALL_SHOW', "All Layers Show", ""),
                   ('ALL_HIDE', "All Layers Hide", ""),
                   ('ALL_INVERT', "ALL Layers Invert", ""),
                   ('SHOW', "Layer Show", ""),
                   ('HIDE', "Layer Hide", ""),
                   ('INVERT', "Layer Iinvert", ""),
                   ),
    )
    @classmethod
    def poll(cls, context):
        sima = context.space_data
        return (sima.image and sima.image.layers_data.layers ) 

    def execute(self, context):
        image = context.space_data.image    
        layers= image.layers_data.layers
        layer_idx = self.layer_idx      
        layer = layers[layer_idx]    
        if  self.has_alt:
            for idx in range(len(layers)):
                bpy.ops.image.layer_visible(layer_idx = idx, visible = "HIDE")
            bpy.ops.image.layer_visible(layer_idx = layer_idx, visible = "SHOW")
            return {'FINISHED'}
        if self.visible == "ALL_SHOW":
            for idx in range(len(layers)):
                bpy.ops.image.layer_visible(layer_idx = idx, visible =  "SHOW") 
            return {'FINISHED'}
        elif self.visible == "ALL_HIDE":
            for idx in range(len(layers)):
                bpy.ops.image.layer_visible(layer_idx = idx, visible =  "HIDE") 
            return {'FINISHED'} 
        elif self.visible == "ALL_INVERT":
            for idx in range(len(layers)):
                bpy.ops.image.layer_visible(layer_idx = idx, visible =  "INVERT") 
            return {'FINISHED'}          
        elif self.visible == "SHOW":
            is_visible = True
        elif self.visible == "HIDE":
            is_visible = False
        elif self.visible == "INVERT":
            is_visible = False if layer.is_visible == True else True            
        layer.is_visible = is_visible
        update_image(image)     
        return {'FINISHED'}

    def invoke(self, context, event):
        self.has_alt = event.alt
        return self.execute(context)


class LayerOpsMenu(bpy.types.Menu):
    """More layers operator"""
    bl_label = "More Operator"
    bl_idname = "image.layer_ops_menu"
    def draw(self, context):
        layout = self.layout
        layout.operator("image.layer_visible", text="Show All Layers", icon="RESTRICT_VIEW_OFF").visible="ALL_SHOW"
        layout.operator("image.layer_visible", text="Hide All Layers", icon="RESTRICT_VIEW_ON").visible="ALL_HIDE"
        layout.operator("image.layer_visible", text="Invert All Layers", icon="RESTRICT_VIEW_OFF").visible="ALL_INVERT"

class LayersPanel(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Layers"     
    bl_category = 'image'

    @classmethod
    def poll(cls, context):
        sima = context.space_data
        return (sima.image and sima.image.layers_data.layers ) 

    def draw(self, context):
        layout = self.layout
        sima = context.space_data
        img = sima.image
        layout.template_ID(sima, "image")
        row = layout.row()
        ImageList(img.layers_data.layers, row)
        col = row.column(align=True)
        col.menu(LayerOpsMenu.bl_idname, icon='DOWNARROW_HLT', text="")

class ImageList(UI_TreeView):
    def draw_item(self, item_layout, layer_idx, space):
        layer = self.layers[layer_idx]
        icon = 'RESTRICT_VIEW_OFF' if layer.is_visible else 'RESTRICT_VIEW_ON'
        btn_visible = item_layout.operator("image.layer_visible", text="", emboss=False, icon=icon)
        btn_visible.layer_idx = layer_idx
        btn_visible.visible = "HIDE" if layer.is_visible else "SHOW"

        for i in range(space*3):
            item_layout.separator()
        if layer.type == "GROUP_START":
            #icon = "TRIA_DOWN" if layer.group_down else  "TRIA_RIGHT"
            icon = "DISCLOSURE_TRI_DOWN" if layer.group_down else  "DISCLOSURE_TRI_RIGHT"
            item_layout.prop(layer, "group_down",text = "", icon = icon, emboss=False)   
            item_layout.prop(layer, "name", text = "", emboss = False, icon = "FILESEL")           
        elif layer.type == "LAYER":    
            item_layout.prop(layer, "name", text = "", emboss = False, icon = "TEXTURE")      


######## data  ##########
class ImageLayerData(bpy.types.PropertyGroup):
    group_down = BoolProperty(name="group down", default=True)
    type = EnumProperty(
            name="Move Direction",
            description="",
            items=(
                        ('GROUP_START', "group start", ""),
                        ('GROUP_END', "group end", ""),
                        ('LAYER', "layer", "")
                   ),
            default = "LAYER"
    )
    name = StringProperty(name="Layer Name", default="new layer")
    is_visible = BoolProperty(name="vis tog", default=True)
    #pixels =  []
    #position = []

class LayersData(bpy.types.PropertyGroup):
    layers = CollectionProperty(type = ImageLayerData)



def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(btn_import_layers_image)
    bpy.types.Image.layers_data = PointerProperty(name = "layers manager", type =  LayersData,  description = "image mesh layers manager data" )


def unregister():
    del bpy.types.Image.layers_data
    bpy.types.INFO_MT_file_import.remove(btn_import_layers_image)
    bpy.utils.unregister_module(__name__)  

if __name__ == "__main__":
    register()



