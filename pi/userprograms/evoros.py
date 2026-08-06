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
                print("Error parsing info")
    except:
        print("Error in received message")

#initialize connection to evodog via ros
def initevoros():
    global pub
    global pubsys
    rospy.init_node("example", anonymous=True)
    pub = rospy.Publisher('/evocar/pub', String, queue_size=5)
    rospy.Subscriber("/evocar/status", String, poslistener, queue_size=5)
    pubsys = rospy.Publisher('/evocar/system', String, queue_size=5)
    time.sleep(0.1)
    for i in range(10):
        pub.publish(String('{"command":"direct","v1":"ignore"}'))
        time.sleep(0.1)


def stop():
    global pubsys
    pubsys.publish(String('{"command":"stop"}' )) 

def command( cmd ):
    global pub
    pub.publish(String('{"command":"direct","v1":"'+cmd+'"}'))
    print(cmd)

def stand():
    command( "stand" )

def walk():
    command( "walk" )

def turnOn():
    command( "on" )
    command( "go" )

def turnOff():
    command( "stop" )
    command( "off" )

def goToBodyPos( durationms, positions ): #milli-seconds
    command( ( "w," + str(durationms) + "," + positions ) )

#example function
def walkFor3Seconds():
    walk()
    time.sleep( 3 )
    stand()

