# -*- coding: utf-8 -*-
import serial
import time
import getch
import sys
from termios import tcflush, TCIOFLUSH
import math
import os
sys.path.insert(1, '../userprograms')
sys.path.insert(1, '../userprograms/apps')
import evosequence
import rospy
import json
import copy
from std_msgs.msg import String
from ReadLine import ReadLine
import threading

quitted = False


def getHomeCommand():
    if os.path.exists( "kits/attached_kits.json" ):
        with open('kits/attached_kits.json') as f:
            j = json.load(f)
        for kit_id in j:
            if j[kit_id]:
                with open("kits/kit_"+kit_id+".json") as f:
                    k = json.load(f)
                if "home_command" in k:
                    return k["home_command"].encode( 'utf-8' )
    return "home"

#roscmd = {}

def send ( string ):
    try:
        #print "sending", string
        ser.write (string)
    except:
        ser.close()
        connect()
        return


# Establish the connection on a specific port
def connect():
    global ser
    baudrate = 115200
    timeout = 0.1
    write_timeout = 0.5

    ports = [ '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1' ]
    for port in ports:
        try:
            print "Trying ", port
            ser = serial.Serial( port, baudrate, timeout = timeout, write_timeout = write_timeout ) # Establish the connection on a specific port
            break
        except:
            print "Could not connect to ", port
            ser = None
connect()
serialRead = ReadLine( ser )
time.sleep(2)
serialRead = ReadLine( ser )
#ser = serial.Serial('/dev/cu.usbserial-AL00YX3I', 115200, timeout = 0.1) #mac
time.sleep(2)
send( getHomeCommand() + "\n" )
time.sleep(2)
send( "on\n" ) #turn on power to arm


def stop():
    global leftSpeed
    global rightSpeed
    leftSpeed = 0
    rightSpeed = 0
    send(" \n")

def obstacleDetected():
    global leftSpeed
    global rightSpeed
    global dist
    if(leftSpeed > 0 or rightSpeed > 0):
        string = ser.readline()
        if( string[0] == 'd' ):
            string = string[1:]
            dist = int(string)
            if ( dist < 150):
                return true

    return false

def drive():
    global leftSpeed
    global rightSpeed
    global dist
    if leftSpeed < -255:
        leftSpeed = 255
    if leftSpeed > 255:
        leftSpeed = 255
    if rightSpeed < -255:
        rightSpeed = 255
    if rightSpeed > 255:
        rightSpeed = 255

    send( ( 'L' + ':' + str(leftSpeed) + '\n' ).encode( 'utf-8' ) )
    send( ( 'R' + ':' + str(rightSpeed) + '\n').encode( 'utf-8' ) )



positions = {
    "a" : 0.0,
    "b" : 0.0,
    "c" : 0.0,
    "d" : 0.0,
    "e" : 0.0,
    "f" : 0.0
}
power = False

xyincr = 5.0

#height
floor_to_sh = 100.276
#from arm base swivel center
center_to_sh = 13.919
sh_to_el = 120.0 #shoulder to elbow
el_to_gr = 118.5 #elbow to gripper
gr_to_ct_x = 122.0 #horiz dist from gripper pivot to beginning of fingers
gr_to_ct_z = 10.0 #vertical dist from gripper pivot to middle height of fingers


#Returns angle between ab and bc
def getangleabc( ab, bc, ca ):
    v = (ab*ab + bc*bc - ca*ca) / (2.0 * ab * bc );
    if ( v > 1.0 ):
        v = 1.0
    if ( v < -1.0 ):
        v = -1.0
    return math.acos(v) #radians

def calcWristPos( angles ):
    b = math.radians( angles['b'] )
    cminusb = math.radians( angles['c'] ) - b;
    radius = center_to_sh + ( sh_to_el * math.cos( b ) + el_to_gr * math.cos( cminusb ) )
    height = sh_to_el * math.sin( b ) - el_to_gr * math.sin( cminusb ) + floor_to_sh

    return {"radius": radius,"height": height }

def calcGripPos( angles ):
    wristpos = calcWristPos( angles )
    #find grip angle from horizontal
    e_horiz = angles['e'] - ( angles['c'] - angles['b'] ) - 90.0;
    #print "e_horiz: ", e_horiz
    e_horiz = math.radians( e_horiz )
    sin_e_horiz = math.sin( e_horiz )
    cos_e_horiz = math.cos( e_horiz )
    gr_z = (gr_to_ct_x * sin_e_horiz ) + (gr_to_ct_z * cos_e_horiz )
    gr_x = (gr_to_ct_x * cos_e_horiz ) - (gr_to_ct_z * sin_e_horiz )
    wristpos['grheight'] = wristpos['height'] + gr_z
    wristpos['grradius'] = wristpos['radius'] + gr_x
    return wristpos

def calcAnglesFromWristPos( radius, height, wrist_angle ):
    #we want to find the wrist angle as if elbow was horizontal
    #fine length of direct line joining shoulder to wrist (l)
    height -= floor_to_sh
    radius -= center_to_sh
    l = math.sqrt( radius * radius + height * height )
    one180minusc = getangleabc( sh_to_el, el_to_gr, l )
    c = math.pi - one180minusc;
    #find angle from horizontal of direct line joining shoulder to wrist (l)
    l_to_horiz = math.atan2( height, radius )
    se_to_l = getangleabc( sh_to_el, l, el_to_gr )
    b = se_to_l + l_to_horiz;
    e = math.radians(wrist_angle) + c - b;
    return { "b": math.degrees(b), "c": math.degrees(c), "e": math.degrees(e) }

def calcAnglesFromGripPos( radius, height, wrist_angle ):
    #first find wrist position from gripper position
    #find angle of gripper from horizontal
    e_horiz = math.radians( wrist_angle - 90.0 )
    sin_e_horiz = math.sin( e_horiz )
    cos_e_horiz = math.cos( e_horiz )
    gr_z = (gr_to_ct_x * sin_e_horiz ) + (gr_to_ct_z * cos_e_horiz )
    gr_x = (gr_to_ct_x * cos_e_horiz ) - (gr_to_ct_z * sin_e_horiz )
    #subtract from position to get wrist position
    radius -= gr_x
    height -= gr_z
    return calcAnglesFromWristPos( radius, height, wrist_angle )

prevchar = ' '
prevtime = 0
prevpos = {}
repeat_count = 0
incr = xyincr #init with default
prev_wrist_from_downward = 90
prevval = 0

def processCommand( str_ ):
    global prevchar
    global prevtime
    global prevpos
    global repeat_count
    global prev_wrist_from_downward
    global prevval

    getcurpos = False
    cmd = ""
    radius = -1 #distance of gripper tip from origin
    height = -1 #height from floor
    vertical = -1 #angle of gripper from vertical downward
    #split by comma
    pieces = str_.split( ",")
    for piece in pieces:
        if piece == "":
            continue
        if piece == 'h' or piece == "home":
            piece = getHomeCommand()
        include_in_output = True
        semicolon = piece.find( ':' )
        if semicolon >= -1: #found
            name = piece[:semicolon]
            val = piece[(semicolon+1): ]
            if name == 'r':
                radius = float(val)
                include_in_output = False
            elif name == 'h':
                height = float(val)
                include_in_output = False
            elif name == 'v':
                vertical = float(val)
                include_in_output = False
            elif name == 'x' or name == 'y':
                getcurpos = True
                include_in_output = False

            if getcurpos:
                ser.write('i\n')
                str_ = ser.readline()
                #print "curpos:", str_ #rg uncommented dec 21, 2020 todo to do
                divideString( str_ ) # updates 'positions'
                str_ = ""
                pos = calcGripPos( positions )
                #print pos
                wrist_from_downward =  positions["b"] - positions["c"] + positions["e"];
                #print "wrist_from_downward:", wrist_from_downward
                curtime = time.time()
                if name == prevchar and (prevtime + 0.2) > curtime: #same key pressed constantly
                    repeat_count += 1
                    #keep same corresponding values to prevent drift
                    wrist_from_downward = prev_wrist_from_downward
                    #print "New wrist_from_downward: ", wrist_from_downward
                    if name == 'x' or name == 'X':
                        pos["grheight"] = prevpos["grheight"] #keep same height since moving horizontally
                        pos["height"] = prevpos["height"]
                        #RG added Dec 21,2020, experimental!! todo to do
                        #since returned value may have drift
                        pos["grradius"] = prevpos["grradius"]# + prevval;
                    elif name == 'y' or name == 'Y':
                        pos["grradius"] = prevpos["grradius"] #keep same radius since moving vertically
                        pos["radius"] = prevpos["radius"]
                        #RG added Dec 21,2020, experimental!! todo to do
                        #since returned value may have drift
                        pos["grheight"] = prevpos["grheight"]# + prevval;
                else:
                    #print "Not continuing"
                    repeat_count = 0

                prevpos = pos
                prevtime = curtime
                prev_wrist_from_downward = wrist_from_downward
                prevchar = name
                prevval = float(val)
                #increment radius or height

                if name == 'x':
                    pos["grradius"] += float(val)
                elif name == 'y':
                    pos["grheight"] += float(val)
                if pos["grradius"] < 25.0:
                    pos["grradius"] = 25.0
                if pos["grheight"] < 0.0:
                    pos["grheight"] = 0.0
                radius = pos["grradius"]
                height = pos["grheight"]
                vertical = wrist_from_downward
                #angles = calcAnglesFromWristPos( pos["radius"], pos["height"], wrist_from_downward )
                #print angles
                #cmd = dictToCmd( angles )


        if include_in_output:
            if cmd == "":
                cmd = piece
            else:
                cmd += "," + piece

    if ( radius >= 20.0 and height >= -10.0 and vertical >= -85.0 ):
        pos = calcAnglesFromGripPos( radius, height, vertical )
        if ( cmd != "" ):
            cmd += ","
        cmd +=  "b:" + ( "%0.3f" % pos["b"] )
        cmd += ",c:" + ( "%0.3f" % pos["c"] )
        cmd += ",e:" + ( "%0.3f" % pos["e"] )
    return cmd


def sendCommand( cmd ):
    global ser
    ser.write( cmd + "\n" )

def divideString( str_ ):
    for i, c in enumerate( str_ ):
        if( c == '\n' or c == '\r' ):
            updatePos( str_ [ :i ] )
            break
        if ( (i+1) == len(str_) ):
            updatePos( str_ )
            break

        if ( c == ',' ):
            updatePos( str_[ 0:i ] )
            str_ = str_[ i+1 : ]
            divideString( str_ )
            break


def updatePos( s ):
    global positions
    global power
    cIndex = -1
    s = s.rstrip()
    #print "s:", s
    for i, c in enumerate( s ):
        if( c == ':' ):
            cIndex = i

    if cIndex != -1 :
        name = s[:cIndex];
        value = s[cIndex+1:]
        #print "Name:", name
        #print "Value:", value
        if (len( name ) == 1 and ( (name[0] >= 'a' and name[0] <= 'f')
            or name[0] =='L' or name[0] == 'R') ):
            servo = name
            deg = float( value )
            positions[ servo ] = deg
        elif name == "pwr":
                if ( value == "1" ):
                    power = True
                else:
                    #print "Setting false"
                    #print value
                    power = False

def increment( char , op):
    ser.write( ( char + ':' + op + '2\n' ).encode( 'utf-8' ) )
    #print ser.readline()

def dictToCmd( angles ):
    cmd = ""
    for servo,angle in angles.items():
        cmd += servo + ":" + ("%0.3f" % angle) + ","
    if ( len( cmd ) >= 1 ):
        cmd = cmd[:-1]
    return cmd #remove last ,


joystickMode = True

if len(sys.argv) > 1:
    arg = 1
    while arg < len(sys.argv):
        if sys.argv[arg] == "-s" and len(sys.argv) > (arg+1):
            time.sleep(1)
            arg += 1
            evosequence.runSequenceFile( sys.argv[arg], processCommand, sendCommand, False) #check keyboard
        arg += 1


def infothread():
        global selfpub
        global quitted

        print "info thread started"
        time.sleep(1)
        while quitted == False and not rospy.is_shutdown():
            selfpub.publish( String('{"command":"action","v1":"k"}') )
            time.sleep(0.2)
        print "info thread quitting"

def sysListener(ros_data):
    global leftSpeed
    global rightSpeed
    global pub
    #print ros_data.data
    try:
        msg = json.loads(ros_data.data)
    except:
        print "Syntax error in " + ros_data.data
        return
    if( msg.has_key('command') ):
        cmd = copy.deepcopy( msg )
        msg = {}
  	#print json.dumps(cmd)
        if( cmd["command"] == "cancel_sequence" ):
            evosequence.cancelSequence()
        elif( cmd["command"] == "stop" or
              cmd["command"] == "exit" or
              cmd["command"] == "quit" ):
            evosequence.cancelSequence()
            rightSpeed = 0
            leftSpeed = 0
            stop()
            drive()
        if ( cmd["command"] == "exit" or
             cmd["command"] == "quit" ):
            ser.write( "off\n" ) #turn arm power off
            rospy.signal_shutdown("Shutting down" )
            sys.exit()


lock = threading.Lock()

error_in_last_sequence = False

def listener(ros_data):
    global positions
    #global roscmd
    global leftSpeed
    global rightSpeed
    global dist
    global ser
    global prevchar
    global prevtime
    global prevpos
    global repeat_count
    global incr
    global prev_wrist_from_downward
    global power
    global error_in_last_sequence

    #print "Current threadid: ", threading.current_thread().ident
    inp = -1;
    #print ros_data.data
    try:
        roscmd = json.loads(ros_data.data)
    except:
        print "Syntax error in " + ros_data.data
        return
    lock.acquire()
    if( roscmd.has_key('command') ):
        cmd = copy.deepcopy( roscmd )
        roscmd = {}
  	#print json.dumps(cmd)
        if( cmd["command"] == "direct" ):
            cmdcmd = processCommand( cmd["v1"] )
            #print cmdcmd
            if ( cmdcmd == "i" ):
                    inp = 'i'
            elif ( cmdcmd == "k" ):
                    inp = 'k'
            elif ( cmdcmd != "" ):
                #print cmdcmd #rg uncommented dec 21, 2020, todo to do
                ser.write( cmdcmd.encode('utf-8') + "\n" )
        elif ( cmd["command"] == "action" ):
            inp = cmd["v1"]
        elif ( cmd["command"] == "sequence" ):
            if ( not evosequence.runSequenceFile( cmd["v1"], processCommand, sendCommand, False) ): #check keyboard
                #publish message so user knows of error
                print "Error while running sequence"
                error_in_last_sequence = True


        if( inp == ord('q') or inp == 'q'):
            leftSpeed = 0
            rightSpeed = 0
            stop()
        elif( inp == "quit" or inp == "exit" ):
            leftSpeed = 0
            rightSpeed = 0
            stop()
            rospy.signal_shutdown("Shutting down" )
            sys.exit()
        elif( inp != -1 ):
            if( inp == 'up' ):
                if(  rightSpeed < 255 and leftSpeed < 255):
        	        leftSpeed += 20
                	rightSpeed += 20
                	drive()

            elif( inp == 'down' ):
                if( leftSpeed  > -255 and rightSpeed > -255 ):
                	leftSpeed -= 20
                	rightSpeed -= 20
                	drive()
            elif( inp == 'right' ):
                leftSpeed += 20
                rightSpeed -= 20
                drive()
            elif( inp == 'left' ):
                leftSpeed -= 20
                rightSpeed += 20
                drive()
            elif ( inp == ord (' ') or inp == ' '):
                rightSpeed = 0
                leftSpeed = 0
            	stop()
                drive()

            elif( (inp >= ord( 'a' ) and inp <= ord( 'f' )) ):
                increment(chr(inp), '+')

            elif( inp >= ord( 'A' ) and inp <= ord( 'F' ) ):
                increment(chr(inp).lower(), '-')

            elif( inp >= 'a' and inp <=  'f'  ):
                increment(inp, '+')

            elif( inp >= 'A' and inp <= 'F' ):
                increment(inp.lower(), '-')

            elif ( inp == 'h' ):
                ser.write( getHomeCommand() + "\n" )

            elif ( inp == 'i' or inp == 'k' ):
                ser.write( ((""+inp) + "\n").encode("utf-8"))
                str_ = ser.readline().rstrip()
                #print str_
                divideString( str_ )
                #print positions
                pos = calcGripPos( positions )
                #print pos
                wrist_from_downward =  positions["b"] - positions["c"] + positions["e"];
                #print "wrist_from_downward:", wrist_from_downward
                #angles = calcAnglesFromGripPos( pos["grradius"], pos["grheight"], wrist_from_downward )
                #print angles
                j = { "pos": str_, "pwr": power,
                      "r": round(pos["grradius"],2),
                      "h": round( pos["grheight"], 2 ),
                      "v": round( wrist_from_downward , 2 ) };
                if ( error_in_last_sequence ):
                    j["err_seq"] = True
                    error_in_last_sequence = False
                pub.publish( String( json.dumps(j) ) )

            elif ( inp == 'x' or inp == 'X' or inp == 'y' or inp == 'Y' ):
                #print inp + " Pressed\n"
                ser.write('i\n')
                str_ = ser.readline()
                #print str_
                divideString( str_ )
                #print positions
                pos = calcGripPos( positions )
                #print pos
                wrist_from_downward =   positions["b"] - positions["c"] + positions["e"];
                #print "wrist_from_downward:", wrist_from_downward

                curtime = time.time()
                if inp == prevchar and (prevtime + 0.1) > curtime: #same key pressed constantly
                    repeat_count += 1
                    if incr < 15.0:
                        incr += 1.0 #make faster while you keep pressed
                    #keep same corresponding values to prevent drift
                    wrist_from_downward = prev_wrist_from_downward
                    #print "New wrist_from_downward: ", wrist_from_downward
                    if inp == 'x' or inp == 'X':
                        pos["grheight"] = prevpos["grheight"] #keep same height since moving horizontally
                        pos["height"] = prevpos["height"]
                    elif inp == 'y' or inp == 'Y':
                        pos["grradius"] = prevpos["grradius"] #keep same radius since moving vertically
                        pos["radius"] = prevpos["radius"]
                else:
                    #print "Not continuing"
                    repeat_count = 0
                    incr = xyincr #init with default

                #print "time diff: %0.2f", curtime - prevtime
                prevpos = pos
                prevtime = curtime
                prev_wrist_from_downward = wrist_from_downward
                prevchar = inp
                #increment radius or height
                #print "incr: ", incr
                if inp == 'x':
                    pos["radius"] += incr
                elif inp == 'X':
                    pos["radius"] -= incr
                elif inp == 'y':
                    pos["height"] += incr
                elif inp == 'Y':
                    pos["height"] -= incr
                angles = calcAnglesFromWristPos( pos["radius"], pos["height"], wrist_from_downward )
                #print angles
                cmd = dictToCmd( angles )
                #print cmd
                ser.write( cmd + "\n" )
                #print ""
                #print ""
    lock.release()


rospy.init_node("myListener")
rospy.Subscriber("/evocar/pub", String, listener, queue_size=5)
rospy.Subscriber("/evocar/system", String, sysListener, queue_size=5)
pub = rospy.Publisher('/evocar/status', String, queue_size=5)
selfpub = rospy.Publisher('/evocar/pub', String, queue_size=5)
print "evoduino running"
t = threading.Thread(target=infothread, name="info")
t.daemon = True
t.start()
rospy.spin()
quitted = True


#Turn arm power off
ser.write( "off\n" )
