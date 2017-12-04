import cv2, time
from grip import GripPipeline

pipeline = GripPipeline()
stream = None
url = 'http://127.0.0.1:1180/?action=stream'
while(True):
    if not stream: stream = cv2.VideoCapture(url)
    connected, frame = stream.read()
    if not connected:
        print('RIP Camera')
        time.sleep(1)
        stream.release()
        stream = None
        continue
    pipeline.process(frame)


