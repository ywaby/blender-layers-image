# part of project bl_layers_image(https://github.com/ywaby/blender-layers-image)
# Copyright (c) 2017 ywaby@163.com
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT


class UI_TreeView():
    """data struct ref layers image"""
    def __init__(self, tree):
        self.tree = tree

    def draw_item(self,
                  item,
                  item_layout: "layout to draw tree item",
                  item_idx: "item index in tree",
                  indent: "item indent"):
        pass

    def draw(self, layout: "layout to draw tree view"):
        tree = self.tree
        indent = 0
        box = layout.box()
        idx = 0
        while idx < len(tree):
            item = tree[idx]
            if item.type == "GROUP_START":
                row = box.row(align=True)
                self.draw_item(item, row, idx, indent)
                if item.group_expand  is False:
                    idx = self.get_group_end_idx(idx)
                else:
                    indent += 1
            elif item.type == "GROUP_END":
                indent -= 1
            elif item.type == "LAYER":
                row = box.row(align=True)
                self.draw_item(item, row, idx, indent)
            idx += 1

    def get_group_end_idx(self, start_idx: "GROUP_START idx"):
        group_layer = 1
        for idx in range(start_idx + 1, len(self.tree)):
            item = self.tree[idx]
            if item.type == "GROUP_START":
                group_layer += 1
            elif item.type == "GROUP_END":
                group_layer -= 1
            if group_layer == 0:
                return idx
        return
