from psd_tools import PSDImage
psd_path = r'E:\develop_space\blender\scripts\bl_layers_image\test\test.psd'

def test_psd_to_bl_image():
    print("test psd_to_bl_image")
    psd = PSDImage.load(psd_path)
    image = psd.as_bl()
    image.name="psd_to_bl_image"

def test_layer_to_bl_image():
    print("test layer_to_bl_image")
    psd = PSDImage.load(psd_path)
    image = psd.layers[0].layers[1].as_bl()
    image.name="layer_to_bl_image"

def test_layers_to_bl_image():
    print("test layers_to_bl_image")
    psd = PSDImage.load(psd_path)
    image = psd.layers[0].as_bl()
    image.name="layers_to_bl_image"

test_psd_to_bl_image()
test_layer_to_bl_image()
test_layers_to_bl_image()