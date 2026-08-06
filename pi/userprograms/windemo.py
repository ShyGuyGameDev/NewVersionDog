from evoros import *

#start ros connection
initevoros()

#add your commands here
#print "Turning on"
#turnOn()

print "Example for going to a position"
#you can use the response of the "i" command from getpos.py or evodogocontrol.py
#goToBodyPos( 2000, "0,38,65,0,38,65,0,-38,-65,0,-38,-65" )
time.sleep( 1 )

#print "Walking for 3 seconds"
#walkFor3Seconds() #example function 

while True:
    stand()
    time.sleep( 3 )

    command( "bow" )
    time.sleep( 5 )

    command( "right" )
    time.sleep( 5 )

    command( "left" )
    time.sleep( 5 )

    command( "forward" )
    time.sleep( 5 )

    command( "stand" )
    time.sleep( 5 )

    command( "tall" )
    time.sleep( 5 )

    command( "stand" )
    time.sleep( 5 )

    #command( "sit" )
    #time.sleep( 6 )

    #command( "getup" )
    #time.sleep( 6 )


