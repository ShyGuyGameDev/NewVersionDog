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
#time.sleep(goToBodyPos( 2000, "0,38,65,0,38,65,0,-38,-65,0,-38,-65" ))
command("stand")
time.sleep(2)
goToBodyPos( 2000, "0,10,65,0,38,65,0, -90,90,0,38,65" )
time.sleep(2)
goToBodyPos( 2000, "0,10,65,0,38,65,0, -90,68,0,38,65" )
time.sleep(2)
goToBodyPos( 2000, "0,10,65,0,38,65,0, -90,90,0,38,65" )
time.sleep(2)
command("stand")
time.sleep(1)
#command("crouch")
#time.sleep)
command("sit")
