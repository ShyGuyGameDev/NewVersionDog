import os
import time
import requests
import cv2
import numpy as np
import json
import rospy
import sys
from std_msgs.msg import String
import requests

print "Press Ctrl-Backslash to quit"

#initialize connection to evoarm via ros
rospy.init_node("example")
pub = rospy.Publisher('/evocar/pub', String, queue_size=5)
pubsys = rospy.Publisher('/evocar/system', String, queue_size=5)
time.sleep(0.1)
for i in range(10):
    pub.publish(String('{"command":"direct","v1":"ignore"}'))
    time.sleep(0.1)

def stop():
    pubsys.publish(String('{"command":"stop"}' )) 

def sequence( name ):
     pub.publish(String('{"command":"sequence","v1":"'+name+'"}'))

def command( cmd ):
     pub.publish(String('{"command":"direct","v1":"'+cmd+'"}'))

def home():
    command( "home" )
#end ros code

print "Loading Models.."
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')

while True:
	print "Fetching image.."
	url = "http://localhost:8000/frame.jpg"
	response = requests.get(url).content
	#convert string data to numpy array
	npimg = np.frombuffer(response, np.uint8)

	#img = cv2.imread('cam.jpg')
	img = cv2.imdecode( npimg, cv2.IMREAD_UNCHANGED )
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

	print "Perfoming face detection.."
 	print "Press Ctrl-Backslash to quit"
	faces = face_cascade.detectMultiScale(gray, 1.3, 5)
	for (x,y,w,h) in faces:
	    img = cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
	    #roi_gray = gray[y:y+h, x:x+w]
	    #roi_color = img[y:y+h, x:x+w]
	    #eyes = eye_cascade.detectMultiScale(roi_gray)
	    #for (ex,ey,ew,eh) in eyes:
	    #    cv2.rectangle(roi_color,(ex,ey),(ex+ew,ey+eh),(0,255,0),2)

            #move arm to follow center of face rectangle
            cx = x + w/2
            cy = y + h/2

            #approximate a angle rotation of base
            #and y coordinate height increase or decrease
            #by finding offset of face rectangle's center from center of image 
            dx = abs(cx - 320)/8
            dy = abs(cy - 240)/8

            if cx < 320:
                cmd = "a:+{dx:.2f}".format( dx = dx)
            else:
                cmd = "a:-{dx:.2f}".format( dx = dx)

            if cy < 240:
                cmd = cmd + "," + "y:+{dy:.2f}".format( dy=dy )
            else:
                cmd = cmd + "," + "y:-{dy:.2f}".format( dy=dy )

            print cmd
            command( cmd )
            

	#write output file so you can see it in browser
	print "Writing to output.jpg"
	cv2.imwrite('/home/pi/system/srv/output.jpg',img)

