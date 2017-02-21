"""
"""
import array
import warnings
from psd_tools.utils import fix_byteorder
from psd_tools.constants import Compression, ChannelID, ColorMode
try:
    import packbits
    import bpy
except ImportError:
    pass
import collections
import numpy


class BBox(collections.namedtuple('BBox', 'x1, y1, x2, y2')):

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1


def psd_bbox_to_bl(base_height, bbox):
    """ base_height PSD height,
        input bbox in psd,
        return bbox in blender image
    """
    x1 = bbox.x1
    y1 = base_height - bbox.y2
    x2 = bbox.x2
    y2 = base_height - bbox.y1
    return BBox(x1, y1, x2, y2)


def psd_xy_to_bl(base_height, x1, y1, x2, y2):
    """ base_height PSD height,
        input xy in psd,
        return xy in blender image
    """
    bl_y1 = base_height - y2
    bl_y2 = base_height - y1
    return x1, bl_y1, x2, bl_y2


def check_format(header):
    '''check psd file data type support or not '''
    if header.depth not in [8]:
        raise Exception("depth = %d  is unsupport" % header.depth)
    if header.color_mode not in [ColorMode.RGB]:
        raise Exception("color_mode =  %s  is unsupport" % header.color_mode)
    return True


def psd_to_bl_image(decoded_data, image=None, image_name=None):
    '''psd file to blender image  pixels data'''
    if not image and not image_name:
        raise Exception("image and image_name cant be None at same time")
    header = decoded_data.header
    check_format(header)
    bl_channels = psd_layer_to_bl_rgba(
        decoded_data.image_data,
        _get_psd_channel_ids(header),
        header.depth,
        BBox(0, 0,header.width,header.height),
        image.use_alpha if image else True
    )
    pixels = bl_rgba_mix(bl_channels)
    if not image:
        image = bpy.data.images.new(
            image_name,  header.width, header.height, alpha=True)
    if image_name:
        image.name = image_name
    image.pixels = pixels
    return image


def layer_to_bl_image(decoded_data, layer_idx, image=None):
    '''psd layer to blender image pixels data'''
    header = decoded_data.header
    layers = decoded_data.layer_and_mask_data.layers
    layer = layers.layer_records[layer_idx]

    bl_channels = psd_layer_to_bl_rgba(
        layers.channel_image_data[layer_idx],
        _get_layer_channel_ids(layer),
        header.depth,
        layer.bbox(),
        image.use_alpha if image else True
    )
    pixels = bl_rgba_mix(bl_channels)
    if not image:
        image = bpy.data.images.new(layer.name, layer.width, layer.height, alpha=True)
    image.pixels = pixels
    return image


def combined_bbox(layers, layer_idxs):
    """
    layers : psd layer_records
    layer_idxs: all layers index(only layers)
    """
    lefts = [layers[layer_idx].left for layer_idx in layer_idxs]
    tops = [layers[layer_idx].top for layer_idx in layer_idxs]
    rights = [layers[layer_idx].right for layer_idx in layer_idxs]
    bottoms = [layers[layer_idx].bottom for layer_idx in layer_idxs]
    return BBox(min(lefts), min(tops), max(rights), max(bottoms))

def layers_to_bl_image(decoded_data, layer_idxs, image_name, image=None):
    '''psd layers in layer_idxs mix and to blender image'''
    if not image and not image_name:
        raise Exception("image and image_name cant be None at same time")
    layers_and_mask = decoded_data.layer_and_mask_data.layers
    layers_rd = layers_and_mask.layer_records
    # filter layer
    layer_idxs = [layer_idx for layer_idx in layer_idxs
                  if layers_rd[layer_idx].width() > 0 or layers_rd[layer_idx].height() > 0]
    header = decoded_data.header
    mix_bbox = combined_bbox(layers_rd, layer_idxs)
    mix_channels = numpy.ones((4, mix_bbox.height, mix_bbox.width))
    mix_channels[3]=0
    for layer_idx in layer_idxs:
        layer = layers_rd[layer_idx]
        if layer.blend_mode != b'norm':
            raise Exception("layer {0:s} :{1:d} type = {2:b} unsupport".format(layer.name, layer_idx, layer.blend_mode))
        layer_channels = psd_layer_to_bl_rgba(
            layers_and_mask.channel_image_data[layer_idx],
            _get_layer_channel_ids(layer),
            header.depth,
            layer.bbox(),
            image.use_alpha if image else True
        )
        bl_layers_nor_mix(mix_channels, mix_bbox, layer_channels, layer.bbox())
    pixels = bl_rgba_mix(mix_channels)
    if not image:
        image = bpy.data.images.new(
            image_name, mix_bbox.width, mix_bbox.height, alpha=True)
    if image_name:
        image.name = image_name
    image.pixels = pixels
    return image

def array_from_raw(data, depth):
    if depth == 1:
        raise Exception("depth = 1 is unsupport")
    elif depth == 8:
        arr = array.array("B", data)
    if depth == 16:
        arr = array.array("I", data)
    elif depth == 32:
        arr = array.array("f", data)
    return fix_byteorder(arr)


def channel_decode(channel, depth, width, height):
    '''psd channel data to full list data 
    [
        [line]
        [line]
    ]
    '''
    channel_data = packbits.decode(
        channel.data) if channel.compression == Compression.PACK_BITS else channel.data
    channel_data = array_from_raw(channel_data, depth)
    bl_channel = numpy.reshape(channel_data, (height, width))
    bl_channel = numpy.flipud(bl_channel)
    return bl_channel


def bl_layers_nor_mix(base_layer, base_bbox, up_layer, up_bbox):
    '''blender layers normal mix'''
    dn_channels = base_layer[:,
                            up_bbox.y1 - base_bbox.y1:up_bbox.y2 - base_bbox.y1,
                            up_bbox.x1 - base_bbox.x1:up_bbox.x2 - base_bbox.x1]
    up_channel_R, up_channel_G, up_channel_B, up_channel_A = up_layer
    dn_channel_R, dn_channel_G, dn_channel_B, dn_channel_A = dn_channels
    mix_channel_R = up_channel_R * up_channel_A + dn_channel_R * \
        dn_channel_A - dn_channel_R * dn_channel_A * up_channel_A
    mix_channel_G = up_channel_G * up_channel_A + dn_channel_G * \
        dn_channel_A - dn_channel_G * dn_channel_A * up_channel_A
    mix_channel_B = up_channel_B * up_channel_A + dn_channel_B * \
        dn_channel_A - dn_channel_B * dn_channel_A * up_channel_A
    mix_channel_A = up_channel_A + dn_channel_A - dn_channel_A * up_channel_A
    base_layer[:, 
    up_bbox.y1 - base_bbox.y1:up_bbox.y2 - base_bbox.y1, 
    up_bbox.x1 - base_bbox.x1:up_bbox.x2 - base_bbox.x1] = [mix_channel_R, mix_channel_G, mix_channel_B, mix_channel_A]
    return


def bl_rgba_mix(bl_channels):
    '''blender layers data rgba mix get image pixels'''
    bl_channel_R, bl_channel_G, bl_channel_B, bl_channel_A = bl_channels
    bl_channel_R = bl_channel_R.ravel()
    bl_channel_G = bl_channel_G.ravel()
    bl_channel_B = bl_channel_B.ravel()
    bl_channel_A = bl_channel_A.ravel()
    pixels = numpy.ravel(
        (bl_channel_R, bl_channel_G, bl_channel_B, bl_channel_A), order='F')
    return pixels.tolist()


def psd_layer_to_bl_rgba(layer_channels, channel_ids, depth, bbox, target_has_alpha):
    ''' psd channels_data to blender  layers data(rgba)
    [[r],
    [g],
    [b],
    [a]]
    '''
    width = bbox.width
    height = bbox.height
    idx = channel_ids.index(ChannelID.RGB_R)
    bl_channel_R = channel_decode(layer_channels[idx], depth, width, height)
    idx = channel_ids.index(ChannelID.RGB_G)
    bl_channel_G = channel_decode(layer_channels[idx], depth, width, height)
    idx = channel_ids.index(ChannelID.RGB_B)
    bl_channel_B = channel_decode(layer_channels[idx], depth, width, height)
    if target_has_alpha:
        try:
            idx = channel_ids.index(ChannelID.TRANSPARENCY_MASK)
            bl_channel_A = channel_decode(layer_channels[idx], depth, width, height)
        except:
            bl_channel_A = numpy.full_like(bl_channel_R, 255)
        bl_channels = numpy.array([bl_channel_R, bl_channel_G, bl_channel_B, bl_channel_A])
    else:
        bl_channels = numpy.array([bl_channel_R, bl_channel_G, bl_channel_B])
    bl_channels = bl_channels / (2**depth - 1)  # int to float
    return bl_channels


def _get_psd_channel_ids(header):
    if header.color_mode == ColorMode.RGB:
        if header.number_of_channels == 3:
            return [0, 1, 2]
        elif header.number_of_channels >= 4:
            return [0, 1, 2, ChannelID.TRANSPARENCY_MASK]
    elif header.color_mode == ColorMode.CMYK:
        if header.number_of_channels == 4:
            return [0, 1, 2, 3]
        elif header.number_of_channels == 5:
            return [0, 1, 2, 3, ChannelID.TRANSPARENCY_MASK]
    elif header.color_mode == ColorMode.GRAYSCALE:
        if header.number_of_channels == 1:
            return [0]
        elif header.number_of_channels == 2:
            return [0, ChannelID.TRANSPARENCY_MASK]
    else:
        warnings.warn("Unsupported color mode (%s)" % header.color_mode)


def _get_layer_channel_ids(layer):
    return [info.id for info in layer.channels]
