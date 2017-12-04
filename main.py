import time
import logging
from cv2 import VideoCapture
from networktables import NetworkTables
from grip import GripPipeline

URL = 'http://127.0.0.1:1180/?action=stream'
TEAM_NUMBER = 3863

NT_SERVER = 'roboRIO-%s-FRC.local' % (TEAM_NUMBER)
NT_TABLE_NAME ='/vision/opencv'

EXTRA_OUTPUT_ATTRS = [] #Output values from Pipeline will be automatically detected.
                        #If for some reason they aren't, put any extra attribues here

class ProcessPipelineWithURL:
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

    def sendPipelineOutput(self):
        pipelineAttrs = self.pipeline.__dict__.keys()
        outputAttrs = [attr for attr in pipelineAttrs if attr.endswith('_output')]
        attrsToOutput = outputAttrs + EXTRA_OUTPUT_ATTRS
        for attr in attrsToOutput:
            prettyAttrName = attr.replace('_output', '')
            try:
                attrValue = getattr(self.pipeline, attr)
            except AttributeError:
                self.logger.error("OpenCV pipeline doesn't have attribute: %s", attr)
                continue
            self.table.putNumberArray(prettyAttrName, attrValue)

    def run(self):
        self.logger.info('Attempting to process camera stream')
        while True:
            frame = self.readStreamFrame()
            if frame:
                self.pipeline.process(frame)
                self.sendPipelineOutput()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    p = ProcessPipelineWithURL(URL, GripPipeline)
    p.run()

