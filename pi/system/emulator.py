import serial
import time
import sys
import os
import rospy
import json
import copy
from std_msgs.msg import String
import signal


obstacle_distance = -1
curpos = ""


def signal_handler(signal,frame):
        print("You pressed Ctrl-C.")
        print("Shutting down ROS communications.")
        rospy.signal_shutdown("Shutting down because Ctrl-C.")
        sys.exit(0)


#Set up Ctrl-C handler if needed, will quit without stopping anything
#signal.signal(signal.SIGINT, signal_handler)

def obstacleDistance():
    global obstacle_distance
    return obstacle_distance


#gets called whenever a message is received
def poslistener( ros_data ):
    global obstacle_distance
    data = json.loads(ros_data.data)
    try:
        info = data["pos"]
        try:
            finallist = info.split(",")
            obstacle_distance = int(finallist[3])
            #print "Distance: ", obstacle_distance
            for x in range(4):
                finallist.pop(0)
                pos = ""
                for element in finallist:
                    pos = pos +str(int(float(element)))+','
                pos = pos[:len(pos)-1] #remove last comma
                curpos = pos
        except:
                print "Error parsing info"
    except:
        print "Error in received message"

def publistener( ros_data ):
    data = json.loads( ros_data.data )
    try:
        print "Received msg", json.dumps(data)
        cmdtype = data["command"]
        if ( cmdtype == "direct" and
             data["v1"].startswith( "w," ) ):
             positions = data["v1"].split(",")
             positions.pop(0) #remove "w"
             positions.pop(0) #remove duration
             pos = ','.join( positions )
             j = { "pos": "info,1,1,-1," + pos }
             print "Publishing " , json.dumps(j)
             pub.publish( String( json.dumps(j)) )
    except:
        print "Error"


#initialize connection to evodog via ros
def initevoros():
    global pub
    rospy.init_node("emulator", anonymous=True)
    pub = rospy.Publisher('/evocar/status', String, queue_size=5)
    rospy.Subscriber("/evocar/pub", String, publistener, queue_size=5)

initevoros()
rospy.spin()
