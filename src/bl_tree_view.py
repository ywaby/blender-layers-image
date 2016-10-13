import bpy
import pdb
import ctypes
class UI_TreeView():
    def __init__(self, layers, layout):
        self.layers = layers
        self.draw(layout)
    
    def draw_item(self, item_layout : "layout to draw tree item", item_idx : "item index in tree", space : "item space "):
        pass
    
    def draw(self, layout:"layout to draw tree view"):

        layers = self.layers
        space = 0
        box = layout.box()
        #for layer in layers:  
        idx = 0
        while(idx < len(layers)) :
            layer = layers[idx]
            if layer.type == "GROUP_START":
                row = box.row(align=True)
                self.draw_item(row,idx,space)
                if layer.group_down == False:
                    idx = self.get_group_end(layers, idx)
                else :
                    space += 1
            elif layer.type == "GROUP_END":
                space -= 1       
            elif layer.type == "LAYER":      
                row = box.row(align=True)
                self.draw_item(row,idx,space)  
            idx+=1
    
    @staticmethod
    def get_group_end(layers, start_idx):
        group_layer = 1
        for idx in range(start_idx+1, len(layers)):
            layer = layers[idx]
            if layer.type == "GROUP_START":
                group_layer+=1
            elif layer.type == "GROUP_END":
                group_layer-=1
            if group_layer == 0:
                return idx                
        return None
