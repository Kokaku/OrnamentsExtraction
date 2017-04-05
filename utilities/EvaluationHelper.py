from imageHandler import getImagePath, readImage, getIntersectingBox, getBoxArea, parseOrnament

def getIoU(box1, box2):
    intersectionBox = getIntersectingBox(box1, box2)
    intersectionArea = getBoxArea(intersectionBox)
    box1Area = getBoxArea(box1)
    box2Area = getBoxArea(box2)
    return intersectionArea / (box1Area + box2Area - intersectionArea)

def findBestIou(ornaments, extractedOrnamentStr):
    extractedOrnament = parseOrnament(extractedOrnamentStr)
    bestScore = 0
    for i in range(len(ornaments)):
        ornament = ornaments[i]
        score = getIoU(ornament, extractedOrnament)

        if score > bestScore:
            bestScore = score

    return bestScore

def getProposalsIou(annotatedPage):
    pagePath = getImagePath(imagesPath+"bookm-"+annotatedPage['bookId']+"/"+annotatedPage['pageId'])
    ornaments = list(map(parseOrnament, annotatedPage['ornaments']))
    extractedOrnaments = annotatedPage['proposals']
    if len(extractedOrnaments) > 0:
        fullImage = readImage(pagePath)
        
    ious = []
    for extractedOrnamentStr in extractedOrnaments:
        ious.append(findBestIou(ornaments, extractedOrnamentStr))
    
    return ious