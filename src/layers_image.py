
import os
from bl_tree_view import UI_TreeView
from psd_tools import PSDImage
from psd_tools.user_api import bl_support
from psd_tools.user_api.psd_image import BBox

import numpy
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

bl_info = {
    "name": "layers image",
    "author": "ywaby",
    "version": (0, 1, 0),
    "blender": (2, 78),
    "description": "import layers image from psd; simple control layers image",
    "wiki_url": "https://github.com/ywaby/blender-layers-image",
    "tracker_url": "https://github.com/ywaby/blender-layers-image/issues",
    "support": "TESTING",
    "location": "UV/image Editor",
    "category": "system"
}

class ImportLayersImage(Operator, ImportHelper):
    """Impot layers image (psd)"""
    bl_idname = "layers_image.import"
    bl_label = "Import Image With Layers"
    filter_glob = StringProperty(
        default="*.psd", options={'HIDDEN'}, maxlen=255)

    def execute(self, context):
        image = self.import_layers_image()
        return {'FINISHED'}

    def import_layers_image(self):
        '''import image with layers(.psd)'''
        filepath = self.filepath
        image = LayersImageManager.get_exist_image(filepath)
        if image:
            LayersImageManager(image).update_image_from_file()
            return
        else:
            psd = PSDImage.load(filepath)
            name = os.path.basename(filepath)
            image = bpy.data.images.new(name, psd.header.width, psd.header.height, alpha=True)
            ImportLayersImage.get_layers_from_psd(psd.decoded_data, psd.layers, image.layers_data)
            image.filepath = filepath
            LayersImageManager(image).layers_mix()
            image.layers_data.import_time = os.path.getmtime(filepath)
            image.pack(as_png=True)
            return image

    @staticmethod
    def get_layers_from_psd(decoded_data, psd_layers, bl_layers_data):
        '''psd data to bl image bl_layers_data'''
        for layer in psd_layers:
            if layer.is_group:
                lm_layer = bl_layers_data.layers.add()
                lm_layer.type = "GROUP_START"
                lm_layer.is_visible = layer.visible
                lm_layer.name = layer.name
                lm_layer.group_expand = not layer.closed
                ImportLayersImage.get_layers_from_psd(decoded_data, layer.layers, bl_layers_data)
                lm_layer = bl_layers_data.layers.add()
                lm_layer.type = "GROUP_END"
            else:  # is real layer
                header = decoded_data.header
                lm_layer = bl_layers_data.layers.add()
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


class LayersImageManager():
    def __init__(self, image):
        self.image = image

    @staticmethod
    def get_exist_image(filepath):
        '''find image or not'''
        for image in bpy.data.images:
            if image.filepath == filepath:
                return image
        return

    def is_modified(self):
        if os.path.exists(self.image.filepath):
            modified_time = os.path.getmtime(self.image.filepath)
            if modified_time > self.image.layers_data.import_time:
                return True
        return False

    def new_image_from_layers(self, start_idx, end_idx):
        layers = self.image.layers_data.layers
        real_layers = LayersImageManager.real_layers_in_layers(
            layers, start_idx, end_idx, only_visible=False)
        c_pos = LayersImageManager.combined_position(real_layers)
        c_bbox = BBox(c_pos[0], c_pos[1], c_pos[2], c_pos[3])
        image_name = layers[start_idx].name
        new_image = bpy.data.images.new(
            image_name, c_bbox.width, c_bbox.height, alpha=True)
        new_layers = new_image.layers_data.layers
        for layer in layers[start_idx:end_idx + 1]:
            new_layer = new_layers.add()
            new_layer.name = layer.name
            new_layer.group_expand = layer.group_expand
            new_layer.type = layer.type
            new_layer.is_visible = layer.is_visible
            if layer.type == "LAYER":
                new_layer["channels"] = layer["channels"]
                new_layer["position"] = LayersImageManager.relative_position(c_pos, layer["position"])
        LayersImageManager(new_image).layers_mix()
        return new_image

    def new_image_from_group(self, group_idx):
        layers = self.image.layers_data.layers
        end_idx = UI_TreeView(layers).get_group_end_idx(group_idx)
        return self.new_image_from_layers(group_idx, end_idx)

    def update_image_from_file(self):
        """update image from psd file"""
        image = self.image
        psd = PSDImage.load(image.filepath)
        image.generated_height = psd.header.height
        image.generated_width = psd.header.width
        image.layers_data.layers.clear()
        ImportLayersImage.get_layers_from_psd(psd.decoded_data, psd.layers, image.layers_data)
        image.layers_data.import_time = os.path.getmtime(image.filepath)
        self.layers_mix()
        image.pack(as_png=True)
        return image

    def layers_mix(self):
        '''
        update layer image from its layers data
        '''
        image = self.image
        layers = self.layers_in_image()
        # filter layer
        layers = [layer for layer in layers
                if layer["position"][3] - layer["position"][1] > 0 or layer["position"][2] - layer["position"][0] > 0]
        base_bbox = BBox(0, 0, image.size[0], image.size[1])
        base_channels = numpy.ones((4, base_bbox.height, base_bbox.width))
        base_channels[3] = 0
        for layer in reversed(layers):
            layer_bbox = BBox(layer["position"][0], layer["position"][1], layer["position"][2], layer["position"][3])
            layer_channels = numpy.array(layer["channels"])
            bl_support.bl_layers_nor_mix(
                base_channels, base_bbox, layer_channels, layer_bbox)
        image.pixels[:] = bl_support.bl_rgba_mix(base_channels)

    def layers_in_image(self, only_visible=True):
        '''get real layers in image '''
        layers = self.image.layers_data.layers
        real_layers = self.real_layers_in_layers(layers, 0, len(layers), only_visible)
        return real_layers

    def layers_in_group(self, group_idx, only_visible=True):
        '''get real layers in group '''
        layers = self.image.layers_data.layers
        end_idx = UI_TreeView.get_group_end_idx(layers, group_idx)
        real_layers = self.real_layers_in_layers(
            layers, group_idx, end_idx, only_visible)
        return real_layers

    @staticmethod
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
                    if layer.is_visible is False:
                        idx = UI_TreeView.get_group_end_idx(from_layers, idx)
                elif layer.type == "LAYER":
                    if layer.is_visible is True:
                        real_layers.append(layer)
                idx += 1
        return real_layers

    @staticmethod
    def combined_position(layers):
        x1 = [layer["position"][0] for layer in layers]
        y1 = [layer["position"][1] for layer in layers]
        x2 = [layer["position"][2] for layer in layers]
        y2 = [layer["position"][3] for layer in layers]
        return min(x1), min(y1), max(x2), max(y2)

    @staticmethod
    def relative_position(base_position, layer_position):
        x1 = layer_position[0] - base_position[0]
        y1 = layer_position[1] - base_position[1]
        x2 = layer_position[2] - base_position[0]
        y2 = layer_position[3] - base_position[1]
        return x1, y1, x2, y2

class UpdateImageFromFile(bpy.types.Operator):
    """Update layers image from filepath"""
    bl_idname = "layers_image.update_image_from_file"
    bl_label = "Update layers image from filepath"

    @classmethod
    def poll(cls, context):
        sima = context.space_data
        return (sima.type == 'IMAGE_EDITOR' and
                sima.image and
                sima.image.layers_data.layers
               )

    def execute(self, context):
        image = context.space_data.image
        LayersImageManager(image).update_image_from_file()
        return {'FINISHED'}

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
               ('INVERT', "Layer Iinvert", "")
              ))

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
        #import profile;profile.runctx("LayersImageManager(image).layers_mix()", globals(), locals(), "test.prof") # TODO: test time cost
        LayersImageManager(image).layers_mix()
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
        image = sima.image
        row = layout.row()
        row.template_ID(sima, "image")

        if LayersImageManager(image).is_modified():
            col = row.column(align=True)
            col.operator(UpdateImageFromFile.bl_idname, text="", icon='HELP')
        row = layout.row()
        LayersTreeView(image.layers_data.layers).draw(row)
        col = row.column(align=True)
        col.menu(LayersOpsMenu.bl_idname, icon='DOWNARROW_HLT', text="")

class LayersTreeView(UI_TreeView):

    def draw_item(self, item, item_layout, layer_idx, indent):
        icon = 'RESTRICT_VIEW_OFF' if item.is_visible else 'RESTRICT_VIEW_ON'
        btn_visible = item_layout.operator(LayerVisible.bl_idname, text="", emboss=False, icon=icon)
        btn_visible.layer_idx = layer_idx
        btn_visible.visible = "HIDE" if item.is_visible else "SHOW"
        for i in range(indent*3):
            item_layout.separator()
        if item.type == "GROUP_START":
            icon = "DISCLOSURE_TRI_DOWN" if item.group_expand else "DISCLOSURE_TRI_RIGHT"
            item_layout.prop(item, "group_expand", text="", icon=icon, emboss=False)
            item_layout.prop(item, "name", text="", emboss=False, icon="FILESEL")
        elif item.type == "LAYER":
            item_layout.prop(item, "name", text="", emboss=False, icon="TEXTURE")


class ImageLayerData(bpy.types.PropertyGroup):
    group_expand = BoolProperty(name="group expand", default=False)
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
    # pixels =  []
    # position = []

class LayersData(bpy.types.PropertyGroup):
    layers = CollectionProperty(type=ImageLayerData)
    import_time = FloatProperty()

def btn_import_layers_image(self, context):
    self.layout.operator(ImportLayersImage.bl_idname, text="Layers Image")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(btn_import_layers_image)
    bpy.types.Image.layers_data = PointerProperty(name="layers manager",
                                                  type=LayersData,
                                                  description="image mesh layers manager data")


def unregister():
    del bpy.types.Image.layers_data
    bpy.types.INFO_MT_file_import.remove(btn_import_layers_image)
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
