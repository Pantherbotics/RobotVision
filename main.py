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
        sortedY = self.sortTupleListByIdx(coords, 1)
        sortedX = self.sortTupleListByIdx(coords, 0)

        largestY = sortedY[0][0]
        smallestY = sortedY[-1][1]
        largestX = sortedX[1][0]
        smallestX = sortedY[-1][1]

        meanX = numpy.mean([largestX, smallestX])
        meanY = numpy.mean([largestY, smallestY])
        return (meanX, meanY)

    def sortTupleListByIdx(self, tupleList, idx):
        return sorted(tupleList, key=lambda x: x[idx])


    def initCurses(self):
        self.writeCurses = True
        self.scr = curses.initscr()

    def sendPipelineOutput(self):
        idx = 0
        contour_list = getattr(self.pipeline, "filter_contours_output")

        if len(contour_list) == 0:
            return

        for contour in contour_list:
            n = "contour_%s" % idx
            width, height, center = processContour(contour)
            self.table.putNumber(n + "_width", width)
            self.table.putNumber(n + "_height", height)
            self.table.putNumberArray(n + "_centerpoint", center)
            if self.writeCurses:
                self.cursesTerminalWrite(contour)
            self.logger.debug('Name: %s type: %s val: %s', n, type(a), a)
            idx += 1
            if self.writeCurses:
                self.cursesTerminalWrite(center, char="X")
            self.logger.debug('Cenerpoint: (%s,%s)', center[1], center[0])

	def processContour(self, contour):
		minXY = numpy.amin(contour, axis = 0)
		maxXY = numpy.amax(contour, axis = 0)
		width = maxXY[0] - minXY[0]
		height = maxXY[1] - minXY[1]
		center = [(maxXY[0] + minXY[0])/2, (maxXY[1] + minXY[1])/2)]
		return [width, height, center]

    def cursesTerminalWrite(self, point, char="#"):
        percent = tuple(map(operator.truediv, point, VIS_SIZE))
        screenPercent = (percent[1], percent[0])
        x, y = tuple(map(operator.mul, screenPercent, self.scr.getmaxyx()))
        try:
            self.scr.addstr(int(x), int(y), str(char))
            self.scr.refresh()
        except BaseException as er:
            print(er)

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
