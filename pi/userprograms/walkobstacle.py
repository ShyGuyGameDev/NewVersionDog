from evoros import *

#start ros connection
initevoros()

#add your commands here
#print "Turning on"
turnOn()

#print "Example for going to a position"
#you can use the response of the "i" command from getpos.py or evodogocontrol.py
#goToBodyPos( 2000, "0,38,65,0,38,65,0,-38,-65,0,-38,-65" )
#time.sleep( 3 )

#print "Walking for 3 seconds"
#walkFor3Seconds() #example function 

#print "Going to stand"
#stand()
#time.sleep( 3 )

command("stand")
time.sleep(3)
command("trotForward")
while True:
	distance=obstacleDistance()
	print(str(distance))
	if distance>0 and distance <100:
		command("stand")
		break
	else:
		time.sleep(0.5)
