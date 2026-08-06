from evoros import *
#for keyboard keypress without blocking
import sys
import select

#Set up Ctrl-C handler only if needed
#signal.signal(signal.SIGINT, signal_handler)

#check if enter pressed to exit program
def enterPressed():
    i,o,e = select.select([sys.stdin],[],[],0.0001)
    for s in i:
        if s == sys.stdin:
            input = sys.stdin.readline()
            return True
    return False

#start ros connection
initevoros()

#add your commands here
print "Turning on"
turnOn()


#keep walking until see obstacle
quit = False
while not quit:
    command( "walk" )
    print "Obstacle Distance: ", obstacle_distance
    
    counter = 0 #dont accept a single bad distance value, get at least 3 before accepting
    while not quit and counter < 3:
        counter = counter + 1
        while ( not quit and ( obstacleDistance() < 0 or obstacleDistance() > 400 ) ) :
            counter = 0
            print "Obstacle Distance: ", obstacleDistance()
            time.sleep(0.1)
            if enterPressed():
                quit = True
        time.sleep(0.1)
    
    command("stand")
    time.sleep( 2 )
    if enterPressed():
        quit = True
        break
    counter = 0
    while not quit and counter < 3:
        counter = counter + 1
        while( not quit and obstacleDistance() > 0 and obstacleDistance() < 400 ):
            counter = 0
            print "Obstacle Distance: ", obstacleDistance()
            time.sleep( 0.2 )
            if enterPressed():
                quit = True
        time.sleep(0.1)


print "Quitting"
stand()
time.sleep(0.2)

