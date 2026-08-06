import rospy
import json
from std_msgs.msg import String

#gets called whenever a message is received
info = "Not received yet"

def poslistener( ros_data ):
	global info
	data = json.loads(ros_data.data)
        text = data["pos"]
	try:
		finallist = text.split(",")
		for x in range(4):
			finallist.pop(0)
		info = ""
		for element in finallist:
			info = info+str(int(float(element)))+','
		info = info[:len(info)-1] #remove last comma
	except:
                print "Error in received message"

#initialize connection to evoarm via ros
rospy.init_node("positionlistener", anonymous=True)
rospy.Subscriber("/evocar/status", String, poslistener, queue_size=5)

cmd = raw_input( "Press enter to see current position of all motors(q to exit) " )
while( cmd != "quit" and cmd != "exit" and cmd != "q" ):
    print( info )
    cmd = raw_input( "Press enter to see current position of all motors(q to exit) " )
