
import os
import pytk
from pytk import BaseNode
import sys

z7 = "\"C:/Program Files/7-Zip/7z.exe\""


class package(BaseNode):
    """package prject to release file (zip)"""
    def action(self):
        os.system(z7+" a dist/layers_image.zip ./src/*")
        os.system(z7+" d dist/layers_image.zip */__pycache__/")


class link(BaseNode):
    """link project to blender addon path(need sudo)"""
    def action(self):
        name = ''
        pass

class release(BaseNode):
    """release project to github"""
    def action(self):
        pass