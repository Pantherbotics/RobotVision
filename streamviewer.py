import cv2

cam = "http://raspberrypi.local:1180/?action = stream"

cap = cv2.VideoCapture(cam)
if not cap:
    print("You're a dumbo! Invalid param for VideoCaputre")


def getframe():
    return cap.read()
