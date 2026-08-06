import numpy as np
import cv2
import requests
import time

print "Loading Models.."
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')

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
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

	print "Perfoming face detection.."
        end_time1 = time.time()
	faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        end_time = time.time()
        print "Time to detect: ", (end_time - end_time1) * 1000
        print "Time overall: ", (end_time - start_time) * 1000
	for (x,y,w,h) in faces:
	    img = cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
	    roi_gray = gray[y:y+h, x:x+w]
	    roi_color = img[y:y+h, x:x+w]
	    eyes = eye_cascade.detectMultiScale(roi_gray)
	    for (ex,ey,ew,eh) in eyes:
	        cv2.rectangle(roi_color,(ex,ey),(ex+ew,ey+eh),(0,255,0),2)

	print "Writing to output.jpg"
	cv2.imwrite('/home/pi/system/srv/output.jpg',img)
