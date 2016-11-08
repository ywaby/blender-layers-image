
import os
import pytk
from pytk import BaseNode
import sys

z7 = "\"D:/Program Files/7-Zip/7z.exe\""


class package(BaseNode):
    """package prject to release file (zip)"""
    def action(self):
        os.system(z7+" a lay1ers_image.zip ./src/*")
        os.system(z7+" d layers_image.zip */__pycache__/")


class link(BaseNode):
    """link project to blender addon path(need sudo)"""
    def action(self):
        name = ''
        link_bl()

class release(BaseNode):
    """release project to github"""
    def action(self):
        github()