import time
import logging
import argparse
import curses
import operator
import numpy
from cv2 import VideoCapture
from networktables import NetworkTables
from grip import GripPipeline

URL = 'http://raspberrypi.local:1180/?action=stream'
TEAM_NUMBER = 3863

NT_SERVER = 'roboRIO-%s-FRC.local' % (TEAM_NUMBER)
NT_TABLE_NAME ='/vision/opencv'

EXTRA_OUTPUT_ATTRS = [] #Output values from Pipeline will be automatically detected.
                        #If for some reason they aren't, put any extra attribues here

VIS_SIZE = (640,480)

class ProcessPipelineWithURL:
    writeCurses = False
    def __init__(self, cameraStreamURL, Pipeline):
        self.url = cameraStreamURL
        self.pipeline = Pipeline()
        self.logger = logging.getLogger('pipeline-procesor')
        self.stream = None
        NetworkTables.setTeam(TEAM_NUMBER)
        NetworkTables.initialize(server=NT_SERVER)
        self.table = NetworkTables.getTable(NT_TABLE_NAME)

    def readStreamFrame(self):
        init = False
        if not self.stream:
            init = True 
            self.stream = VideoCapture(self.url)
        connected, frame = self.stream.read()
        if not connected:
            self.logger.warning('Camera stream could not be read')
            time.sleep(1)
            self.stream.release()
            self.stream = None
            return None
        else:
            if init:
                self.logger.debug('Stream status: %s', connected)
            return frame

    def calcCenterpoint(self):
        attrValue = getattr(self.pipeline, "filter_contours_output")
        if len(attrValue) == 0: return
        coords = [c[0].tolist() for c in attrValue[0]]
        largestY = self.sortTupleListByIdx(coords, 0)
        smallestY = self.sortTupleListByIdx(coords, 0).reverse()
        largestX = self.sortTupleListByIdx(coords, 1)
        smallestX = self.sortTupleListByIdx(coords, 1).reverse()

        meanX = numpy.mean([largestX, smallestX])
        meanY = numpy.mean([largestY, smallestY])
        return (meanY, meanX)
        
    def sortTupleListByIdx(self, tupleList, idx):
        return sorted(tupleList, key=lambda x: x[idx])


    def initCurses(self):
        self.writeCurses = True
        self.scr = curses.initscr()

    def sendPipelineOutput(self):
        idx = 0
        attrValue = getattr(self.pipeline, "filter_contours_output")

        if len(attrValue) == 0:
            return

        if self.writeCurses:
            self.scr.clear()
        coords = [c[0].tolist() for c in attrValue[0]]

        for a in coords:
            n = "filter_contours_%s" % idx
            self.table.putNumberArray(n, a)
            if self.writeCurses:
                self.cursesTerminalWrite(a)
            #self.logger.debug('Name: %s type: %s val: %s', n, type(a), a)
            idx += 1
        center = self.calcCenterpoint()
        self.table.putNumberArray('centerpoint' center)
        if self.writeCurses:
                self.cursesTerminalWrite(center, char="X")
        self.logger.debug('Cenerpoint: (%s,%s)', center[1], center[0])
        

    def cursesTerminalWrite(self, point, char="#"):
        percent = tuple(map(operator.truediv, point, VIS_SIZE))
        x, y = tuple(map(operator.mul, percent, self.scr.getmaxyx()))
        try:
            self.scr.addstr(int(x), int(y), str(char))
            self.scr.refresh()
        except:
            pass

    def run(self):
        self.logger.info('Attempting to process camera stream')
        while True:
            frame = self.readStreamFrame()
            if not frame is None:
                self.pipeline.process(frame)
                self.sendPipelineOutput()

if __name__ == '__main__':
    
    p = ProcessPipelineWithURL(URL, GripPipeline)

    parser = argparse.ArgumentParser(description='Vision Processing')
    parser.add_argument('--curses', action='store_true', 
                       help='Enable curses ouput')
    args = parser.parse_args()
    if args.curses:
        logging.basicConfig(level=logging.CRITICAL)
        p.initCurses()
    else:
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        p.run()
    except BaseException as er:
        if args.curses:
            curses.endwin()
        raise er


