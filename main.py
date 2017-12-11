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

    def sortTupleListByIdx(self, tupleList, idx):
        return sorted(tupleList, key=lambda x: x[idx])

    def initCurses(self):
        self.writeCurses = True
        self.scr = curses.initscr()

    def processContour(self, contour):
        self.logger.debug("Contour: \n %s", contour)
        x_values = []
        y_values = []
        self.logger.debug("Getting x-values and y-values of contour")
        for arr in contour:
            x_values.append(arr[0][0])
            y_values.append(arr[0][1])
        self.logger.debug("Calculating max and min")
        x_max = numpy.max(x_values)
        y_max = numpy.max(y_values)
        x_min = numpy.min(x_values)
        y_min = numpy.min(y_values)

        self.logger.debug("Calculating width and height")
        width = x_max - x_min
        height = y_max - y_min

        self.logger.debug("Calculating center")
        center = ((x_max+x_min)/2, (y_max+y_min)/2)
        self.logger.debug("Contour height: %s, width: %s, center: %s", height, width, center)
        return width, height, center

    def sendPipelineOutput(self):
        self.logger.debug("start of sendPipelineOutput class")
        idx = 0
        self.logger.debug("get contour list from pipeline")
        contour_list = getattr(self.pipeline, "filter_contours_output")

        if len(contour_list) == 0:
            return

        self.logger.debug("iterating through contour list")
        for contour in contour_list:
            n = "contour_%s" % idx
            self.logger.debug("processing the contour")
            width, height, center = self.processContour(contour)
            self.logger.debug("send width, height, center to networktables")
            self.table.putNumber(n + "_width", width)
            self.table.putNumber(n + "_height", height)
            self.table.putNumberArray(n + "_centerpoint", center)
            self.logger.debug('Name: %s height: %s width: %s center: %s', n, height, width, center)
            idx += 1
            if self.writeCurses:
                self.cursesTerminalWrite(center, char="X")
                #self.cursesTerminalWrite(contour) 
            self.logger.debug('Centerpoint: (%s,%s)', center[1], center[0])


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
            self.logger.debug("read frame")
            frame = self.readStreamFrame()
            if not frame is None:
                self.logger.debug("Sending frame to GRIP pipeline")
                self.pipeline.process(frame)
                self.logger.debug("Start sending to rio")
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
