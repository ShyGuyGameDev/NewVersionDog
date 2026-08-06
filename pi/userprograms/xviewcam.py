from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2


#run this script to view the camera feed
#on an X server

camera = PiCamera()
camera.resolution = (320, 240)
camera.framerate = 15
rawCapture = PiRGBArray(camera, size=(320, 240))
# allow the camera to warmup
time.sleep(0.1)
# capture frames from the camera
for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	image = frame.array
	# show the frame
	cv2.imshow("Frame", image)
	key = cv2.waitKey(1) & 0xFF
	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
	if key == ord("q"):
		break
