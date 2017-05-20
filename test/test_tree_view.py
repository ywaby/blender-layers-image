"""
test bl_tree_view module
"""
import bpy
from bl_tree_view import UI_TreeView
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



class LayerData(bpy.types.PropertyGroup):
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



class LayersPanel(bpy.types.Panel):
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_label = "Test TreeView"
    bl_category = 'Test'

    def draw(self, context):
        layout = self.layout
        LayersTreeView(bpy.data.texts[0].test_tree).draw(layout)


class LayersTreeView(UI_TreeView):
    def draw_item(self, item, item_layout, layer_idx, indent):
        icon = 'RESTRICT_VIEW_OFF' if item.is_visible else 'RESTRICT_VIEW_ON'
        item_layout.prop(item, "is_visible", text="", icon=icon, emboss=False)
        for i in range(indent * 3):
            item_layout.separator()
        if item.type == "GROUP_START":
            icon = "DISCLOSURE_TRI_DOWN" if item.group_expand else "DISCLOSURE_TRI_RIGHT"
            item_layout.prop(item, "group_expand", text="",
                             icon=icon, emboss=False)
            item_layout.prop(item, "name", text="",
                             emboss=False, icon="FILESEL")
        elif item.type == "LAYER":
            item_layout.prop(item, "name", text="",
                             emboss=False, icon="TEXTURE")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Text.test_tree = CollectionProperty(type=LayerData)
    bpy.data.texts[0].test_tree.add().type = "GROUP_START"
    bpy.data.texts[0].test_tree.add().type = "LAYER"
    bpy.data.texts[0].test_tree.add().type = "LAYER"
    bpy.data.texts[0].test_tree.add().type = "LAYER"
    bpy.data.texts[0].test_tree.add().type = "GROUP_START"
    bpy.data.texts[0].test_tree.add().type = "LAYER"
    bpy.data.texts[0].test_tree.add().type = "LAYER"
    bpy.data.texts[0].test_tree.add().type = "LAYER"
    bpy.data.texts[0].test_tree.add().type = "GROUP_END"
    bpy.data.texts[0].test_tree.add().type = "GROUP_END"

def unregister():
    del bpy.types.Text.test_tree
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
