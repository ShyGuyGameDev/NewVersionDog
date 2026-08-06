import rospy
import json
from std_msgs.msg import String

#gets called whenever a message is received
def poslistener( ros_data ):
	data = json.loads(ros_data.data)
	print( json.dumps( data ) )

#initialize connection to evoarm via ros
rospy.init_node("positionlistener")
rospy.Subscriber("/evocar/status", String, poslistener, queue_size=5)


rospy.spin() 
