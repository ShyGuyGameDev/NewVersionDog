import rospy
import json
from std_msgs.msg import String
import time

#gets called whenever a message is received
info = "Not received yet"
xyz = "Not received yet"
actual_pos = "Not received yet"

def poslistener( ros_data ):
	global info
	data = json.loads(ros_data.data)
        try:
            info = data["pos"]
            actual_pos = data["apos"]
            xyz = data["xyz"] 
        except:
            print "Error in received message"

def printInfo():
        global info
	try:
		finallist = info.split(",")
                print "Power: ", ("On" if finallist[1] == "1" else "Off")
                print "Enabled: ", ("Yes" if finallist[2] == "1" else "No")
                print "Obstacle Distance: ", finallist[3]
		for x in range(4):
			finallist.pop(0)
                print "Motor Positions:"
		pos = ""
		for element in finallist:
			pos = pos +str(int(float(element)))+','
		pos = pos[:len(pos)-1] #remove last comma
                print pos
	except:
                print "Error parsing info"
                        
#initialize connection to evoarm via ros
rospy.init_node("evodogcontrol", anonymous=True)
rospy.Subscriber("/evocar/status", String, poslistener, queue_size=5)
pub = rospy.Publisher('/evocar/pub', String, queue_size=5)
time.sleep(0.1)

#needing to prime ros sometimes
for i in range(10):
    pub.publish(String('{"command":"direct","v1":"ignore"}'))
    time.sleep(0.1)

def command( cmd ):
    cmd = cmd.strip()
    if cmd == "":
        return
    pub.publish(String('{"command":"direct","v1":"'+cmd+'"}'))
    print( "Sending ", cmd)



cmd = raw_input( "Type command to send to evodog (i for current pos, q to exit) " )
while( cmd != "quit" and cmd != "exit" and cmd != "q" ):
    if cmd == "i":
        printInfo() 
    else:
        command( cmd )
    cmd = raw_input( "Type command to send to evodog (i for current pos, q to exit) " )
