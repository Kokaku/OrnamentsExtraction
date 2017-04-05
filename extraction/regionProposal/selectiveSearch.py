import cv2
import json
import os
import sys
import numpy as np
import selectivesearch
import argparse
from multiprocessing import Pool
from functools import partial

parser = argparse.ArgumentParser(description='Process scan image to propose regions.')
parser.add_argument('pageListJson', type=str, help='filepath of json file that contains list of pages')
parser.add_argument('outputFolder', type=str, help='Output folder path')
parser.add_argument('-r', '--resize', action="store", dest='resize', type=int, nargs='?', help='Resize largest edge of input image to given value and keep aspect ration')
parser.add_argument('-sc', '--scale', action="store", dest='scale', type=int, nargs='?', help='scale')
parser.add_argument('-sg', '--sigma', action="store", dest='sigma', type=float, nargs='?', help='sigma')
parser.add_argument('-ms', '--minsize', action="store", dest='minsize', type=int, nargs='?', help='min size')
parser.add_argument('-p', '--process', action="store", dest='process', type=int, nargs='?', help='number of process')
args = parser.parse_args()

imagesPath = '/mnt/Ornaments_IMG/'
annotatedPagesJsonPath = args.pageListJson

def getImagePath(path):
    if os.path.isfile(path+".tif"):
        path += ".tif"
    elif os.path.isfile(path+".jp2"):
        path += ".jp2"
    else:
        print("Unknown format: {0}".format(pagePath))
    
    return path

def selectiveSearch(resize, scale, sigma, minsize, folderPath, annotatedPage):
    imagePath = getImagePath(imagesPath+"bookm-"+annotatedPage['bookId']+"/"+annotatedPage['pageId'])
    outputPath = '{0}{1}-{2}.json'.format(folderPath, annotatedPage['bookId'], annotatedPage['pageId'])
        
    img = cv2.imread(imagePath,0)

    ratio = 1
    if resize != None and resize > 0:
        ratio = max((img.shape[1]/float(resize), img.shape[0]/float(resize)))
        img = cv2.resize(img, ((int)(img.shape[1]/ratio), (int)(img.shape[0]/ratio)))

    if len(img.shape) < 3:
        img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)

    img_lbl, regions = selectivesearch.selective_search(img, scale=scale, sigma=sigma, min_size=minsize)
    candidates = list(map(lambda r: {'x': r['rect'][0]*ratio,
                                     'y': r['rect'][1]*ratio,
                                     'w': r['rect'][2]*ratio,
                                     'h': r['rect'][3]*ratio}, regions))

    jsonFile = open(outputPath, "w")
    jsonFile.write(json.dumps({'candidates': candidates}, indent=4, sort_keys=True))
    jsonFile.close()
    
    
scale = args.scale
if scale == None:
    scale = 500

sigma = args.sigma
if sigma == None:
    sigma = 0.9

minsize = args.minsize
if minsize == None:
    minsize = 100
    
numProcess = args.process
if numProcess == None:
    numProcess = 20
    
annotatedPagesJson = open(annotatedPagesJsonPath).read()
annotatedPages = json.loads(annotatedPagesJson)['annotatedPages']
selectiveSearchSingleArg = partial(selectiveSearch, args.resize, scale, sigma, minsize, args.outputFolder)
threads = Pool(processes=numProcess, maxtasksperchild=100)
for result in threads.imap_unordered(selectiveSearchSingleArg, annotatedPages):
    pass

threads.close()
threads.terminate()
threads.join()

