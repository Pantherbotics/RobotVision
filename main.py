import streamviewer
from grip import GripPipeline

pipeline = GripPipeline
while(True):
    pipeline.process(streamviewer.getframe())

