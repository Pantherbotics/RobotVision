import time
import logging
import argparse
import curses
import operator
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

    def initCurses(self):
        self.writeCurses = True
        self.scr = curses.initscr()

    def sendPipelineOutput(self):
        idx = 0
        attrValue = getattr(self.pipeline, "filter_contours_output")
        for arr in attrValue[0]:
            a = arr[0].tolist()
            n = "filter_contours_%s" % idx
            self.table.putNumberArray(n, a)
            if self.writeCurses:
                self.cursesTerminalWrite(a)
            self.logger.debug('Name: %s type: %s val: %s', n, type(a), a)
            idx += 1

    def cursesTerminalWrite(self, point):
        percent = tuple(map(operator.truediv, point, VIS_SIZE))
        x, y = tuple(map(operator.mul, percent, self.scr.getmaxyx()))
        self.scr.addstr(int(x), int(y), '#')
        self.scr.refresh()

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


