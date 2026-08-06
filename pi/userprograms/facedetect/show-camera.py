import numpy as np
import cv2
import requests
import time

#you must start the camera service before
#running this. An X server needs to be running on your
#computer if you are not on Linux


while True:
	print "Fetching image.."
        start_time = time.time()
	url = "http://localhost:8000/frame.jpg"
	response = requests.get(url).content
	#convert string data to numpy array
	npimg = np.frombuffer(response, np.uint8)

	#img = cv2.imread('cam.jpg')
	img = cv2.imdecode( npimg, cv2.IMREAD_UNCHANGED )
        end_time1 = time.time()
        print "Time to download: ", (end_time1 - start_time) * 1000
	#gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

	cv2.imshow('frame',img)
	cv2.waitKey(1)
