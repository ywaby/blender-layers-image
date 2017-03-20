bl_info = {
    "name": "layers_image",
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
from bl_tree_view import UI_TreeView
from psd_tools import PSDImage
from psd_tools.user_api import bl_support
from psd_tools.user_api.psd_image import BBox

import numpy
###### utils ##########

def layers_in_image(image, only_visible=True):
    '''get real layers in image '''
    layers = image.layers_data.layers
    real_layers = real_layers_in_layers(layers, 0, len(layers), only_visible)
    return real_layers


def layers_in_group(image, group_idx, only_visible=True):
    '''get real layers in group '''
    layers = image.layers_data.layers
    end_idx = UI_TreeView.get_group_end(layers, group_idx)
    real_layers = real_layers_in_layers(
        layers, group_idx, end_idx, only_visible)
    return real_layers


def real_layers_in_layers(from_layers, start_idx, end_idx, only_visible=True):
    '''get real image data layer form layers'''
    if not only_visible:
        real_layers = [layer for layer in from_layers[
            start_idx:end_idx + 1] if layer.type == "LAYER"]
    else:
        real_layers = []
        idx = start_idx
        while idx < end_idx:
            layer = from_layers[idx]
            if layer.type == "GROUP_START":
                if layer.is_visible == False:
                    idx = UI_TreeView.get_group_end(from_layers, idx)
            elif layer.type == "LAYER":
                if layer.is_visible == True:
                    real_layers.append(layer)
            idx += 1
    return real_layers


def combined_position(layers):
    x1 = [layer["position"][0] for layer in layers]
    y1 = [layer["position"][1] for layer in layers]
    x2 = [layer["position"][2] for layer in layers]
    y2 = [layer["position"][3] for layer in layers]
    return min(x1), min(y1), max(x2), max(y2)


def relative_position(base_position, layer_position):
    x1 = layer_position[0] - base_position[0]
    y1 = layer_position[1] - base_position[1]
    x2 = layer_position[2] - base_position[0]
    y2 = layer_position[3] - base_position[1]
    return x1, y1, x2, y2

###### import #####


def btn_import_layers_image(self, context):
    self.layout.operator(ImportLayersImage.bl_idname, text="Layers Image")


class ImportLayersImage(Operator, ImportHelper):
    """Impot layers image (psd)"""
    bl_idname = "layers_image.import"
    bl_label = "Import Image With Layers"
    filter_glob = StringProperty(
        default="*.psd", options={'HIDDEN'}, maxlen=255)

    def execute(self, context):
        img = import_layers_image(self.filepath)
        img.pack(as_png=True)
        return {'FINISHED'}


def get_layers_from_psd(decoded_data, psd_layers, layers_data):
    '''psd data to bl image layers_data'''
    for layer in psd_layers:
        if layer.is_group:
            lm_layer = layers_data.layers.add()
            lm_layer.type = "GROUP_START"
            lm_layer.is_visible = layer.visible
            lm_layer.name = layer.name
            lm_layer.group_down = not layer.closed
            get_layers_from_psd(decoded_data, layer.layers, layers_data)
            lm_layer = layers_data.layers.add()
            lm_layer.type = "GROUP_END"
        else:
            # is real layer
            header = decoded_data.header
            lm_layer = layers_data.layers.add()
            lm_layer.type = "LAYER"
            lm_layer.is_visible = layer.visible
            lm_layer.name = layer.name
            bbox = layer.bbox
            lm_layer["position"] = bl_support.psd_xy_to_bl(
                header.height, bbox.x1, bbox.y1, bbox.x2, bbox.y2)
            layers_rd = decoded_data.layer_and_mask_data.layers
            layer_rd = layers_rd.layer_records[layer._index]
            layer_bbox = BBox(layer_rd.left, layer_rd.top, layer_rd.right, layer_rd.bottom)
            bl_channels = bl_support.psd_layer_to_bl_rgba(
                layers_rd.channel_image_data[layer._index],
                bl_support._get_layer_channel_ids(layer_rd),
                header.depth,
                layer_bbox,
                target_has_alpha=True
            )
            lm_layer["channels"] = bl_channels.tolist()
    return


def exist_image_from_path(filepath):
    '''had import image or not'''
    for image in bpy.data.images:
        if image.filepath == filepath:
            return image
    return None


def import_layers_image(filepath):
    '''import image with layers(.psd)'''
    image = exist_image_from_path(filepath)
    if image:
        return update_image_from_psd(image, filepath)
    psd = PSDImage.load(filepath)
    name = os.path.basename(filepath)
    image = bpy.data.images.new(
        name, psd.header.width, psd.header.height, alpha=True)
    get_layers_from_psd(psd.decoded_data, psd.layers, image.layers_data)
    image.filepath = filepath
    update_image(image)

    return image


def update_image_from_psd(image, filepath):
    psd = PSDImage.load(filepath)
    image.generated_height = psd.header.height
    image.generated_width = psd.header.width
    image.layers_data.layers.clear()
    get_layers_from_psd(psd.decoded_data, psd.layers, image.layers_data)
    update_image(image)
    return image

###### layer manager #########


def new_image_from_layers(from_layers, start_idx, end_idx):
    real_layers = real_layers_in_layers(
        from_layers, start_idx, end_idx, only_visible=False)
    c_pos = combined_position(real_layers)
    c_bbox = BBox(c_pos[0], c_pos[1], c_pos[2], c_pos[3])
    image_name = from_layers[start_idx].name
    new_image = bpy.data.images.new(
        image_name, c_bbox.width, c_bbox.height, alpha=True)
    new_layers = new_image.layers_data.layers
    for layer in from_layers[start_idx:end_idx + 1]:
        new_layer = new_layers.add()
        new_layer.name = layer.name
        new_layer.group_down = layer.group_down
        new_layer.type = layer.type
        new_layer.is_visible = layer.is_visible
        if layer.type == "LAYER":
            new_layer["channels"] = layer["channels"]
            new_layer["position"] = relative_position(c_pos, layer["position"])
    update_image(new_image)
    return new_image


def new_image_from_group(from_layers, group_idx):
    end_idx = UI_TreeView.get_group_end(from_layers, group_idx)
    return new_image_from_layers(from_layers, group_idx, end_idx)

def read_one_by_one(pixels):
    x=0
    for px in pixels:
        x=x+px

def update_image(image):
    ''' update layer image from its layers data
    '''
    layers = layers_in_image(image)
    # filter layer
    layers = [layer for layer in layers
              if layer["position"][3] - layer["position"][1] > 0 or layer["position"][2] - layer["position"][0] > 0]
    base_bbox = BBox(0, 0, image.size[0], image.size[1])
    base_channels = numpy.ones((4, base_bbox.height, base_bbox.width))
    base_channels[3]=0
    import time
    start_CPU = time.clock()# test time     
    for layer in reversed(layers):
        layer_bbox = BBox(layer["position"][0], layer["position"][1], layer["position"][2], layer["position"][3])
        layer_channels =  numpy.array(layer["channels"])
        bl_support.bl_layers_nor_mix(base_channels, base_bbox,layer_channels, layer_bbox)    
    end_CPU = time.clock()
    print("bl_layers_nor_mix time : %f CPU seconds" % (end_CPU - start_CPU))    
    start_CPU = time.clock()# test time     
    image.pixels[:] = bl_support.bl_rgba_mix(base_channels)
    end_CPU = time.clock()
    print("bl_rgba_mix time : %f CPU seconds" % (end_CPU - start_CPU))

class LayerVisible(bpy.types.Operator):
    """Show/hide  layer (alt to show only)"""
    bl_idname = "layers_image.layer_visible"
    bl_label = "Show/Hide Layer"
    bl_options = {'REGISTER', 'UNDO'}
    layer_idx = IntProperty(default=-1)
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
              )
    )

    @classmethod
    def poll(cls, context):
        sima = context.space_data
        return (sima.type == 'IMAGE_EDITOR' and
                sima.image and
                sima.image.layers_data.layers
               )

    def execute(self, context):
        image = context.space_data.image
        layers = image.layers_data.layers
        layer_idx = self.layer_idx
        layer = layers[layer_idx]
        if self.has_alt:
            for lyer in layers:
                lyer.is_visible = False
            layer.is_visible = True
        if self.visible == "ALL_SHOW":
            for lyer in layers:
                lyer.is_visible = True
        elif self.visible == "ALL_HIDE":
            for lyer in layers:
                lyer.is_visible = False
        elif self.visible == "ALL_INVERT":
            for lyer in layers:
                lyer.is_visible = False
        elif self.visible == "SHOW":
            layer.is_visible = True
        elif self.visible == "HIDE":
            layer.is_visible = False
        elif self.visible == "INVERT":
            layer.is_visible = not layer.is_visible

        update_image(image)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.has_alt = event.alt
        return self.execute(context)


class LayersOpsMenu(bpy.types.Menu):
    """More layers operator"""
    bl_label = "More Operator"
    bl_idname = "layers_image.layer_ops_menu"

    def draw(self, context):
        layout = self.layout
        layout.operator(LayerVisible.bl_idname, text="Show All Layers",
                        icon="RESTRICT_VIEW_OFF").visible = "ALL_SHOW"
        layout.operator(LayerVisible.bl_idname, text="Hide All Layers",
                        icon="RESTRICT_VIEW_ON").visible = "ALL_HIDE"
        layout.operator(LayerVisible.bl_idname, text="Invert All Layers",
                        icon="RESTRICT_VIEW_OFF").visible = "ALL_INVERT"


class LayersPanel(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Layers"
    bl_category = 'image'

    @classmethod
    def poll(cls, context):
        sima = context.space_data
        return (sima.image and sima.image.layers_data.layers)

    def draw(self, context):
        layout = self.layout
        sima = context.space_data
        img = sima.image
        layout.template_ID(sima, "image")
        row = layout.row()
        ImageList(img.layers_data.layers, row)
        col = row.column(align=True)
        col.menu(LayersOpsMenu.bl_idname, icon='DOWNARROW_HLT', text="")


class ImageList(UI_TreeView):

    def draw_item(self, item_layout, layer_idx, space):
        layer = self.layers[layer_idx]
        icon = 'RESTRICT_VIEW_OFF' if layer.is_visible else 'RESTRICT_VIEW_ON'
        btn_visible = item_layout.operator(
            LayerVisible.bl_idname, text="", emboss=False, icon=icon)
        btn_visible.layer_idx = layer_idx
        btn_visible.visible = "HIDE" if layer.is_visible else "SHOW"

        for i in range(space * 3):
            item_layout.separator()
        if layer.type == "GROUP_START":
            #icon = "TRIA_DOWN" if layer.group_down else  "TRIA_RIGHT"
            icon = "DISCLOSURE_TRI_DOWN" if layer.group_down else "DISCLOSURE_TRI_RIGHT"
            item_layout.prop(layer, "group_down", text="",
                             icon=icon, emboss=False)
            item_layout.prop(layer, "name", text="",
                             emboss=False, icon="FILESEL")
        elif layer.type == "LAYER":
            item_layout.prop(layer, "name", text="",
                             emboss=False, icon="TEXTURE")


######## data  ##########
class ImageLayerData(bpy.types.PropertyGroup):
    group_down = BoolProperty(name="group down", default=False)
    type = EnumProperty(
        name="Move Direction",
        description="",
        items=(
            ('GROUP_START', "group start", ""),
            ('GROUP_END', "group end", ""),
            ('LAYER', "layer", "")
        ),
        default="LAYER"
    )
    name = StringProperty(name="Layer Name", default="new layer")
    is_visible = BoolProperty(name="vis tog", default=True)
    #pixels =  []
    #position = []


class LayersData(bpy.types.PropertyGroup):
    layers = CollectionProperty(type=ImageLayerData)


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(btn_import_layers_image)
    bpy.types.Image.layers_data = PointerProperty(name="layers manager", type=LayersData, description="image mesh layers manager data")


def unregister():
    del bpy.types.Image.layers_data
    bpy.types.INFO_MT_file_import.remove(btn_import_layers_image)
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
