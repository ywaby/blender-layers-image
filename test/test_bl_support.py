
import bpy
import psd_tools
from psd_tools import PSDImage
from psd_tools.user_api import bl_support
from psd_tools.user_api.psd_image import BBox
psd_path = r'E:\develop_space\blender\scripts\bl_layers_image\test\test.psd'

def test_psd_to_bl_image():
    print("test psd_to_bl_image")
    psd = PSDImage.load(psd_path)
    image = psd.as_bl()
    image.name="psd_to_bl_image"

def test_layer_to_bl_image():
    print("test layer_to_bl_image")
    psd = PSDImage.load(psd_path)
    import pdb; pdb.set_trace()    
    image = psd.layers[0].layers[1].as_bl()
    image.name="psd_to_bl_image"

def test_layers_to_bl_image():
    print("test layers_to_bl_image")
    psd = PSDImage.load(psd_path)
    import pdb; pdb.set_trace() 
    image = psd.layers[0].layers[0].as_bl()
    image.name="psd_to_bl_image"

test_psd_to_bl_image()
test_layer_to_bl_image()
test_layers_to_bl_image()