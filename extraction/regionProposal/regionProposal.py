import json
import os
import time
from subprocess import Popen, PIPE
import tempfile

def bash_command(cmd):
	"""
	Run a bash command

    Parameters
    ----------
    cmd: string
    	The bash command to be run
	"""

    output = Popen(cmd, shell=True, executable='/bin/bash', stdout=PIPE, stderr=PIPE)
    error = output.stderr.read().decode('utf8').strip()
    if len(error) >= 1:
        print(error)
    output = output.stdout.read().decode('utf8').strip()
    if len(output) >= 1:
        print(output)

def get_windows(image_fnames_txt, cmd='edge_boxes_wrapper', resize=500, alpha=0.65,
                beta=0.55, minScore=0.01, maxBoxes=10000, numThreads=20):
    """
    Run MATLAB EdgeBoxes code on the given image filenames to
    generate window proposals.

    Parameters
    ----------
    image_fnames_txt: string
        Path to a TXT file that contains images paths. Each path are new line separated.
    cmd: string
        edge boxes function to call:
            - 'edge_boxes_wrapper' for effective detection proposals paper configuration.
	resize: integer
		If this value is positive, resize the image such that the largest side has this value of pixels
		while keeping the same aspect ratio.
	alpha: float
		Step size of sliding window search
	beta: float
		Nms threshold for object proposals
	minScore: float
		Min score of boxes to detect
	maxBoxes: integer
		Max number of boxes to detect
	numThreads: integer
		Number of workers
    """
    # Form the MATLAB script command that processes images and write to
    # temporary results file.
    f, output_filename = tempfile.mkstemp(suffix='.mat')
    os.close(f)
    command = "{}('{}', '{}', {}, {}, {}, {}, {}, {})".format(cmd, image_fnames_txt, output_filename, resize,
                                                          alpha, beta, minScore, maxBoxes, numThreads)

    # Execute command in MATLAB.
    mc = "matlab -nodisplay -nosplash -r \"try; {}; catch; exit; end; exit\"".format(command)
    pid = subprocess.Popen(
        shlex.split(mc), stdout=open('/dev/null', 'w'), cwd=script_dirname)
    retcode = pid.wait()
    if retcode != 0:
        raise Exception("Matlab script did not exit successfully!")

    # Read the results and undo Matlab's 1-based indexing.
    all_boxes = list(scipy.io.loadmat(output_filename)['all_boxes'][0])
    subtractor = np.array((1, 1, 0, 0, 0))[np.newaxis, :]
    all_boxes = [boxes - subtractor if len(boxes)>0 else boxes for boxes in all_boxes]

    # Remove temporary file, and return.
    os.remove(output_filename)
    
    return all_boxes

def processSelectiveSearch(pagesToProcessJsonPath, destination, resize=512, scale=512, sigma=0.9,
                           minSize=100, numProcess=20):
	"""
	Run selective search on given images to propose regions of interest.
	Generate one JSON file for each page.

	Note that this function assume the use of anaconda with an environment named "py27" with python 2.7

	Parameters
	----------
	pagesToProcessJsonPath: string
		A path to a JSON file that contains the list of pages to be processed
		The JSON file contains one field: "annotatedPages" which is a list of "bookId" and "pageId"
	destination: string
		A path to a folder in which results will be written.
	resize: integer
		If this value is positive, resize the image such that the largest side has this value of pixels
		while keeping the same aspect ratio.
	scale: integer
		Free parameter. Higher means larger clusters in felzenszwalb segmentation.
	sigma: float
		Width of Gaussian kernel for felzenszwalb segmentation.
	minSize: integer
		Minimum component size for felzenszwalb segmentation.
	numProcess: integer
		Number of workers
	"""

    if not os.path.isdir(destination):
        os.mkdir(destination);
    
    activatePy2 = 'source activate py27'
    currentFolder = os.path.dirname(os.path.realpath('test.py'))
    selectiveSearchCmd = 'python '+currentFolder+'/selectiveSearch.py'
    command = '{} && {} {} {} -r {} -sc {} -sg {} -ms {} -p {}'.format(activatePy2, selectiveSearchCmd,
                pagesToProcessJsonPath, destination, resize, scale, sigma, minSize, numProcess)
    startTime = time.time()
    bash_command(command)
    elapsedTime = time.time() - startTime
    timeReportFile = open(destination+'time.txt', 'w')
    timeReportFile.write("{}\n".format(elapsedTime))
    timeReportFile.close()
    
def processEdgeBoxes(pagesToProcessTxtPath, destination, resize=512, alpha=0.65, beta=0.55, minScore=0.01,
					 maxBoxes=10000, numThreads=20):
	"""
	Run edge boxes on given images to propose regions of interest.
	Generate one JSON file for each page.

	Note that this function assume mathlab with Piotr's MATLAB toolbox (https://pdollar.github.io/toolbox/)
	is installed.

	Parameters
	----------
	pagesToProcessTxtPath: string
		A path to a TXT file that contains images paths. Each path are new line separated.
	destination: string
		A path to a folder in which results will be written.
	resize: integer
		If this value is positive, resize the image such that the largest side has this value of pixels
		while keeping the same aspect ratio.
	alpha: float
		Step size of sliding window search
	beta: float
		Nms threshold for object proposals
	minScore: float
		Min score of boxes to detect
	maxBoxes: integer
		Max number of boxes to detect
	numThreads: integer
		Number of workers
	"""

    if not os.path.isdir(destination):
        os.mkdir(destination);
        
    startTime = time.time()
    boxes = get_windows(pagesToProcessTxtPath, resize=resize, alpha=alpha, beta=beta,
                        minScore=minScore, maxBoxes=maxBoxes, numThreads=numThreads)
    elapsedTime = time.time() - startTime
    timeReportFile = open(destination+'time.txt', 'w')
    timeReportFile.write("{}\n".format(elapsedTime))
    timeReportFile.close()
    
    pagesToProcessTxt = open(pagesToProcessTxtPath, 'r')
    line = pagesToProcessTxt.readline()
    annotatedPageIndex = 0
    while line != '':
        bookId, pageId = line.split('/')[-2:]
        bookId = bookId.split('-')[1]
        pageId = pageId.split('.')[0]
        outputPath = '{0}{1}-{2}.json'.format(folderPath, bookId, pageId)
        
        candidates = list(map(lambda x: {
            'x': x[0],
            'y': x[1],
            'w': x[2],
            'h': x[3],
            }, boxes[annotatedPageIndex]))
        annotatedPageIndex += 1
        
        jsonFile = open(outputPath, "w")
        jsonFile.write(json.dumps({'candidates': candidates}, indent=4, sort_keys=True))
        jsonFile.close()
        line = pagesToProcessTxt.readline()
        
    pagesToProcessTxt.close()