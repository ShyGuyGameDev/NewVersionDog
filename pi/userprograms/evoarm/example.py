import serial
import time
import sys
import os
import rospy
import json
import copy
from std_msgs.msg import String

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

#add your commands here
#a thru f for motors from base to gripper
#a:60 for absolute, or a:+4 for incremental

command( "a:70,b:70,c:120,d:50" )
time.sleep(2)
#use the 's' prefix with a scale factor for speed, e.g
command( "s:0.2,a:90")
time.sleep( 2 )


home()

#stop any sequence
stop()
