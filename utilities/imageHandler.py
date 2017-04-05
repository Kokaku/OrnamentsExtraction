import cv2
import os
import numpy as np
from functools import partial


def getImagePath(path):
    if os.path.isfile(path+".tif"):
        path += ".tif"
    elif os.path.isfile(path+".jp2"):
        path += ".jp2"
    else:
        print("Unknown format: {0}".format(path))
    
    return path

def readImage(imagePath):
    return cv2.imread(imagePath,0)
    
def getIntersectingBox(b1, b2):
    x1 = max(b1['x'], b2['x']);
    y1 = max(b1['y'], b2['y']);
    x2 = min(b1['x'] + b1['w'], b2['x'] + b2['w']);
    y2 = min(b1['y'] + b1['h'], b2['y'] + b2['h']);
    
    if x1 >= x2 or y1 >= y2:
        return None

    return {
        'x': x1,
        'y': y1,
        'w': x2 - x1,
        'h': y2 - y1
    }

def getBoxArea(b1):
    if b1 == None:
        return 0
    return b1['w'] * b1['h']

def parseOrnament(ornament):
    return {
        'x' :round(float(ornament['x'])),
        'y' :round(float(ornament['y'])),
        'w' :round(float(ornament['w'])),
        'h' :round(float(ornament['h'])),
    }

def getCropImage(ornamentBox, img):
    return img[ornamentBox['y']:ornamentBox['y']+ornamentBox['h'], ornamentBox['x']:ornamentBox['x']+ornamentBox['w']]

def padImage(img):
    longer_side = max(img.shape)
    horizontal_padding = (longer_side - img.shape[0]) // 2
    vertical_padding = (longer_side - img.shape[1]) // 2

    return cv2.copyMakeBorder(img, horizontal_padding, horizontal_padding,
                              vertical_padding, vertical_padding,
                              cv2.BORDER_CONSTANT, value=[255, 255, 255])

def squareResizeImage(img, size):
    return cv2.resize(padImage(img), (size, size))
