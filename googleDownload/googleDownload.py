import json
import os
import shutil
import wget
from pathlib import Path
from lxml import html
from subprocess import Popen, PIPE
import hashlib
import zipfile
import multiprocessing
from multiprocessing import Pool
from multiprocessing import Process
import time
import argparse
import sys

parser = argparse.ArgumentParser(description='Download and decrypt book from google books.')
parser.add_argument('bookListJson', type=str, help='filepath of json file that contains list of book ids')
parser.add_argument('outputFolder', type=str, help='Output folder path')
parser.add_argument('tmpFolder', type=str, help='Temporary folder path for download')
parser.add_argument('passphrase', type=str, help='Passphrase for decryption')
parser.add_argument('-m', '--mode', action="store", dest='mode', type=str, nargs='?', help='Execution mode: Info, Preprocess, Download')
parser.add_argument('-p', '--process', action="store", dest='process', type=int, nargs='?', help='number of process')
args = parser.parse_args()

if not os.path.isfile(args.bookListJson):
	print("Error: path {} is not a valid file".format(args.bookListJson))
	sys.exit()

if not os.path.isdir(args.outputFolder):
	print("Error: path {} is not a valid folder".format(args.outputFolder))
	sys.exit()

if not os.path.isdir(args.tmpFolder):
	print("Error: path {} is not a valid folder".format(args.tmpFolder))
	sys.exit()

os.chdir(args.tmpFolder)

def readListToDownload(bookListJson, outputFolder):
    """
    Load book id to be downloaded

    Parameters
    ----------
    bookListJson: string
        Path to a JSON file that contains a field name 'vids': a list of book ids
    outputFolder: string
        Path to the folder of downloaded books

    return: dict(integer, bool)
        A dictionary of book id and status of downlaod. (True if already downloaded)
    """

	jsonBooks = open(bookListJson).read()
	vidsStatus = dict(map(lambda x: (x[4:], False), json.loads(jsonBooks)['vids']))
	return checkListStatus(vidsStatus, outputFolder)

def checkListStatus(vidsStatus, outputFolder):
    """
    Check if a book in vidsStatus is already downloaded

    Parameters
    ----------
    vidsStatus: dict(integer, bool)
        A dictionary of book id and status of downlaod
    outputFolder: string
        Path to the folder of downloaded books

    return: dict(integer, bool)
        A dictionary of book id and status of downlaod. (True if already downloaded)
    """

	for filename in os.listdir(outputFolder):
	    if filename.endswith('.zip'):
	        vidsStatus[filename.split('-')[1].split('.')[0]] = True
	return vidsStatus

def getDownlaodCount(vidsStatus, verbose=True):
    """
    Count the number of book downloaded

    Parameters
    ----------
    vidsStatus: dict(integer, bool)
        A dictionary of book id and status of downlaod
    verbose: bool
        Verbose level

    return: integer
        The number of books downloaded
    """

	finished = 0;
	for vid in vidsStatus:
	    if vidsStatus[vid]:
	        finished += 1
	if verbose:
		print("Downloaded: {0}/{1}".format(finished, len(vidsStatus)))

	return finished

def preprocessList(vidsStatus):
    """
    Request Google server to preprocess books. After this you typically need to wait 7-14 days.

    Parameters
    ----------
    vidsStatus: dict(integer, bool)
        A dictionary of book id and status of downlaod
    """

	print("Request preprocessing:")
	for vid in vidsStatus:
	    if not vidsStatus[vid]:
	        result = triggerProcess(vid)
	        if result != 'Success':
	            print("{}: {}".format(vid, result))
	print("")
	print("Finished sending request. Please wait a few days.")

def triggerProcess(vid):
    url = 'https://books.google.com/libraries/BCUL/_process?barcodes={0}&process_format=html'.format(vid)
    filename = wget.download(url)
    resultFilename = "{0}process/{1}.html".format(folderPath, vid)
    shutil.move(filename, resultFilename)
    
    contents = Path(resultFilename).read_text()
    htmlTree = html.fromstring(contents)
    result = htmlTree.xpath('//div[@id="Main"]/table/tr/td[2]/div/pre/text()')[0]
    return result

def executeCommand(command):
    p = Popen (command, stdout=PIPE)
    out = p.communicate ()
    for line in out[0].decode("utf-8").split('\n'):
        if not line == '':
            print(line)

def decrypt(vid, passphrase):
    encryptedFilename = '{0}.tar.gz.gpg'.format(vid)
    gpgCommand = ['gpg', '--yes', '--batch', '--passphrase='+passphrase, folderPath+'gpg/'+encryptedFilename]
    executeCommand(gpgCommand)

def uncompress(vid):
    compressedFilename = '{0}.tar.gz'.format(vid)
    uncompressCommand = ['tar', '-zxf', folderPath+'gpg/'+compressedFilename, '-C', folderPath+'gpg/'+vid]
    executeCommand(uncompressCommand)

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def checkFiles(decompressedFolder):
    """
    Check if files are decompressed corretly with checksums.

    Parameters
    ----------
    decompressedFolder: String
        Folder of decompressed book

    return: bool
        True if no error detected, False otherwise
    """

    checksumFilepath = decompressedFolder+'checksum.md5'
    if not os.path.isfile(checksumFilepath):
        return False
    
    with open(checksumFilepath) as f:
        lines = f.readlines()
        for line in lines:
            entry = line.strip().split('  ')

            filepath = decompressedFolder + entry[1]
            if not os.path.isfile(filepath) or not md5(filepath) == entry[0]:
                return False
            
    return True

def zipdir(path, zipFilename):
    """
    Zip the folder given in 'path'

    Parameters
    ----------
    path: String
        Path to the folder to be zipped
    zipFilename: string
        Filename to give to the zipball
    """

    ziph = zipfile.ZipFile(zipFilename, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file), file)
    ziph.close()

def downlaodBook(vid):
    url = 'https://books.google.com/libraries/BCUL/{0}.tar.gz.gpg'.format(vid)
    filename = wget.download(url, out=folderPath+'gpg')
    return filename

def downlaodAndProcess(vid, passphrase):
    """
    Download, decrypt, and archive the book corresponding to 'vid'

    Parameters
    ----------
    vid: string
        The book id to be downloaded and processed
    passphrase: string
        Passphrase for decryption

    return: bool
        True if no error, False otherwise
    """

    filename = downlaodBook(vid)
    decompressedFolder = folderPath+'gpg/'+vid+'/'
    shutil.move(filename, '{}gpg/{}.tar.gz.gpg'.format(folderPath, vid))
    decrypt(vid)
    os.mkdir(decompressedFolder) 
    uncompress(vid)
    if not checkFiles(decompressedFolder):
        return False
        
    zipFilename = outputFolder+'bookm-'+vid+'.zip'
    zipdir(decompressedFolder, zipFilename)
    os.remove('{0}gpg/{1}.tar.gz.gpg'.format(folderPath, vid))
    os.remove('{0}gpg/{1}.tar.gz'.format(folderPath, vid))
    shutil.rmtree(decompressedFolder)
    return True

def readyForDownload(vid, getStatus=False):
    """
    Check if the book corresponding to 'vid' is ready for download (if the Google preprocessing is finished).

    Parameters
    ----------
    vid: String
        The book id to be checked
    getStatus: bool
        False: Default. When set to False, return True when ready, False otherwise
        True: When set to True, return the book status

    return: bool or string
        getStatus is False:
            True if book is ready for download, False otherwise
        getStatus is True:
            The book status
    """

    url = 'https://books.google.com/libraries/BCUL/_barcode_search?execute_query=true&barcodes={0}&format=text&mode=full'.format(vid)
    filename = wget.download(url, out=folderPath[:-1])
    contents = Path(filename).read_text()
    os.remove(filename)
    table = contents.split('\n')
    if len(table) < 2 or table[1] == '':
        return False
    indexStatus = table[0].split('\t').index("State")
    status = table[1].split('\t')[indexStatus]
    if getStatus:
        return status
    return status == 'CONVERTED'

def countReadyForDownlaod(vidsStatus):
    count = 0
    for vid in vidsStatus:
        if not vidsStatus[vid]:
            if readyForDownload(vid):
                count += 1

    return count

def getBooksReadyForDownload(bookTerminate, readyQueue):
    """
    Put books ready for downlaod in the queue (for multiprocessing)
    """

    for vid in vidsStatus:
        if not vidsStatus[vid]:
            if readyForDownload(vid):
                while readyQueue.qsize() > 100:
                    time.sleep(1)

                readyQueue.put(vid)

    bookTerminate.value = 1

def downloadManager(bookTerminate, readyQueue, resQueue, passphrase):
    """
    Donwload and process books in the ready queue (for multiprocessing)
    """

    while bookTerminate.value == 0:
        try:
            vid = readyQueue.get(timeout=10)
            resQueue.put((vid, downlaodAndProcess(vid, passphrase)))
        except:
            pass

def startMultiProcessDownload(passphrase, numProcess=10):
    """
    Create and start workers for multiprocessing downlaod

    Parameters
    ----------
    passphrase: String
        Passphrase to decrypt donwloaded files
    numProcess: integer
        Number of workers
    """

    multManager = multiprocessing.Manager()
	readyQueue = multManager.Queue()
	resQueue = multManager.Queue()
	bookTerminate = multManager.Value('i', 0)

	pManager = Process(target=getBooksReadyForDownload, args=(bookTerminate, readyQueue))
	pManager.start()

	jobs = []
	for i in range(numProcess):
	    p = Process(target=downloadManager, args=(bookTerminate, readyQueue, resQueue, passphrase))
	    p.start()
	    jobs.append(p)

    pManager.joint()
    for job in jobs:
        job.joint()

def printMultiProcessProgress():
    """
    Print the progress of multiprocess downloader
    """

	processed = finished
	while bookTerminate.value == 0:
	    try:
	        result = resQueue.get(timeout=10)
	        processed += 1
	        print('{0}/{1}'.format(processed, len(vidsStatus)))
	    except:
	        pass

folderPath = args.tmpFolder
outputFolder = args.outputFolder
vidsStatus = readListToDownload(args.bookListJson, outputFolder)

if not outputFolder.endswith('/'):
    outputFolder = outputFolder + '/'

if args.mode == 'Preprocess':
    preprocessList(vidsStatus)
elif args.mode == 'Download':
    startMultiProcessDownload(args.passphrase, numProcess=args.process)
else:
    print("INFO")
    print("---------")
    getDownlaodCount(vidsStatus, verbose=True)
    print("{} Books ready for downlaod".format(countReadyForDownlaod(vidsStatus))
    