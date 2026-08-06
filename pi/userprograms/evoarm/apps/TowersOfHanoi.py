#Towers Of Hanoi
#IT IS YOUR EXERCISE TO MAKE THIS WORK FOR YOUR EVOARM!

#use python syntax
#the 'sequence' variable must be an array of objects
#with each object having "command" and "delay" (in seconds), and optionally "speed" (as factor of the default 1.0 )

#common positions to make easy to change
#measurements are in millimeters, mm
# 1inch  = 25.4mm

#angle offset, change if entire system seems to have shifted rotationally
# a is the angle of base swivel motor
a_offset = 0 

#heights

#change this when tower set is moved
#base_above_floor = 34
base_above_floor = 8

tower_base_height = 48  
ring_above_base = 7
lowest_ring = base_above_floor + tower_base_height + ring_above_base

#change a and r when tower set is moved
# a is the angle of base swivel motor
# r is the radius, or distance of gripper from center of arm swivel base
a = [ 104 + a_offset, 91 + a_offset, 79 + a_offset ] #angles of 'a' motor, from left to right
r = [265, 260, 265] # dist in mm, or radius from center of base    # 265, 260, 265

f = [53, 57, 59] #how much to close gripper for each ring size

h = [lowest_ring + 18, lowest_ring + 10, lowest_ring]  #heights of each ring, top to bottom
drop = lowest_ring + 32 #drop height at top of tower  
above = lowest_ring + 60 #high above tower

cmdfmt = "v:90,r:{},h:{},a:{}" #v=>angle of gripper from vertical downwards, r=>radius, h=>height, a=>angle of a motor
dropcmd = "f:82" #dont open all the way, don't want to hit neighbors
grabcmd = "f:{}" #not too tight

#common wait times, seconds
quick = 0.25
fast = 1
fastish = 1.5
slow = 2

TOP = 0
MID = 1
BOT = 2

SMALL = 0
MED   = 1
LARGE = 2

LEFT =   0
CENTER = 1
RIGHT  = 2


def fromTo( tower_from, ring_pos, ring_size, tower_to ): #0 left, 1 mid, 2 right
    seq = [
        { "command": cmdfmt.format(r[tower_from], above,   a[tower_from] ), "delay": 0.75, "speed": 1},  
        { "command": cmdfmt.format(r[tower_from], h[ring_pos], a[tower_from] ), "delay": 0.75, "speed": 1},
        { "command": grabcmd.format( f[ring_size] ),                        "delay": 0.5, "speed": 2},
        { "command": cmdfmt.format(r[tower_from], above, a[tower_from] ),   "delay": 0.6, "speed": 1},
        { "command": cmdfmt.format(r[tower_from], above+5, (a[tower_from]+a[tower_to])/2),   "delay": 0.75, "speed": 1},
        { "command": cmdfmt.format(r[tower_to],   above, a[tower_to] ),     "delay": abs(tower_to-tower_from)*0.35, "speed": 0.75}, 
        { "command": cmdfmt.format(r[tower_to],   drop , a[tower_to] ),     "delay": 0.5,"speed": 0.75}, 
        { "command": dropcmd,                                               "delay": 0.5,"speed": 2 }, 
        { "command": cmdfmt.format(r[tower_to], above, a[tower_to] ),       "delay": quick, "speed": 1.0}, #quick
    ]
    return seq

sequence = [
     { "command": dropcmd,          "delay": 0  }, #dont keep open all the way, too wide
     { "command" : cmdfmt.format(r[LEFT], above, a[LEFT] ), "delay": 0.5  }
]

#The Towers Of Hanoi Algorithm, manually implemented
#from left tower to right
sequence.extend( fromTo( LEFT,   TOP, SMALL, RIGHT ) )
sequence.extend( fromTo( LEFT,   MID, MED,   CENTER) )
sequence.extend( fromTo( RIGHT,  BOT, SMALL, CENTER) )
sequence.extend( fromTo( LEFT,   BOT, LARGE, RIGHT) )
sequence.extend( fromTo( CENTER, MID, SMALL, LEFT) )
sequence.extend( fromTo( CENTER, BOT, MED, RIGHT) )
sequence.extend( fromTo( LEFT,   BOT, SMALL, RIGHT) )
sequence.append( {"command": "home", "delay": 2 } )


#from right to left
sequence.append( { "command" : cmdfmt.format(r[RIGHT], above, a[RIGHT] ), "delay": 1.0  } )

sequence.extend( fromTo( RIGHT,  TOP, SMALL, LEFT ) )
sequence.extend( fromTo( RIGHT,  MID, MED, CENTER) )
sequence.extend( fromTo( LEFT,   BOT, SMALL, CENTER) )
sequence.extend( fromTo( RIGHT,  BOT, LARGE, LEFT) )
sequence.extend( fromTo( CENTER, MID, SMALL, RIGHT) )
sequence.extend( fromTo( CENTER, BOT, MED, LEFT) )
sequence.extend( fromTo( RIGHT,  BOT, SMALL, LEFT) )
sequence.append( {"command": "home", "delay": 2 } )


# sequence.append( {"command": "home", "delay": 1 } )
#sequence.append( {"command": "loop" } )