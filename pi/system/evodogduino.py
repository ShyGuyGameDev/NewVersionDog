# -*- coding: utf-8 -*-
import serial
import time
import getch
import sys
from termios import tcflush, TCIOFLUSH
import math
import os
import os.path
import glob
sys.path.insert(1, '../userprograms')
sys.path.insert(1, '../userprograms/apps')
import evosequence
import rospy
import json
import copy
from std_msgs.msg import String
import threading
from evodogikin import *

quitted = False
ser = None
ser_port = None
ser_baud = None

#baud rates used across Evodyne dog/arm boards; probe all until firmware answers
BAUD_CANDIDATES = [ 500000, 115200, 250000, 57600 ]
FALLBACK_BAUD = 500000

#roscmd = {}

def send ( string ):
    global ser
    if ser is None:
        reconnect()
    if ser is None:
        print "No serial connection, dropping command"
        return
    #the firmware WEDGES (stops serving serial until power cycle) if
    #'go' arrives before its calibration offsets are registered.
    #Route 'go' through the verified path instead of sending it blindly.
    stripped = string.strip()
    if stripped == "go":
        safeGo()
        return
    try:
        #print "sending", string
        ser.write (string)
    except:
        print "Serial write failed, reconnecting"
        reconnect()
        try:
            #retry once instead of silently dropping the command
            ser.write (string)
        except:
            print "Command dropped after reconnect"

def sendCommand( cmd ):
    send( cmd + "\n" )

def listSerialPorts():
    """Return /dev/ttyUSB* and /dev/ttyACM* devices that exist right now."""
    ports = sorted( glob.glob( '/dev/ttyUSB*' ) + glob.glob( '/dev/ttyACM*' ) )
    #keep a stable preference order: USB adapters first, then ACM
    preferred = [ '/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB1' ]
    ordered = []
    for p in preferred:
        if p in ports and p not in ordered:
            ordered.append( p )
    for p in ports:
        if p not in ordered:
            ordered.append( p )
    return ordered

def probePort( port, baudrate ):
    """
    Open port@baud, wait for Arduino auto-reset, send 'i', and look for an
    'info' reply. Returns an open Serial on success, or None.
    """
    timeout = 0.1
    write_timeout = 0.5
    s = None
    try:
        print "Trying ", port, "@", baudrate
        s = serial.Serial( port, baudrate, timeout = timeout, write_timeout = write_timeout )
    except Exception as e:
        print "Could not open ", port, "@", baudrate, ":", e
        return None
    try:
        #opening toggles DTR and resets the Arduino; wait for it to boot
        time.sleep( 2.5 )
        try:
            s.flushInput()
        except:
            pass
        s.write( "i\n" )
        reply = ""
        deadline = time.time() + 1.0
        while time.time() < deadline:
            chunk = s.read( 256 )
            if chunk:
                reply += chunk
        if "info" in reply:
            print "CONNECTED", port, "@", baudrate
            print "Firmware reply:", reply.replace( "\r", "\\r" ).replace( "\n", "\\n" )
            return s
        print "No firmware handshake on", port, "@", baudrate, "(got:", repr( reply[:80] ), ")"
    except Exception as e:
        print "Probe failed on", port, "@", baudrate, ":", e
    try:
        s.close()
    except:
        pass
    return None

def connectFallback( ports ):
    """Old behavior: open first available port at 500000 with no handshake."""
    global ser, ser_port, ser_baud
    if not ports:
        ports = [ '/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB1' ]
    for port in ports:
        try:
            print "Fallback open ", port, "@", FALLBACK_BAUD
            ser = serial.Serial( port, FALLBACK_BAUD, timeout = 0.1, write_timeout = 0.5 )
            ser_port = port
            ser_baud = FALLBACK_BAUD
            print "OPENED (no handshake)", port, "@", FALLBACK_BAUD
            return
        except:
            print "Could not connect to ", port
            ser = None
            ser_port = None
            ser_baud = None

# Establish the connection: probe every port/baud until firmware answers
def connect():
    global ser, ser_port, ser_baud
    prev_port = ser_port
    prev_baud = ser_baud
    ser = None
    ser_port = None
    ser_baud = None

    ports = listSerialPorts()
    if not ports:
        print "No /dev/ttyUSB* or /dev/ttyACM* devices found"
        connectFallback( [] )
        return

    print "Serial candidates:", ports
    #if we already found a working combo earlier, try it first on reconnect
    try_first = []
    if prev_port and prev_baud:
        try_first.append( ( prev_port, prev_baud ) )
    for port in ports:
        for baud in BAUD_CANDIDATES:
            if ( port, baud ) not in try_first:
                try_first.append( ( port, baud ) )

    for port, baud in try_first:
        s = probePort( port, baud )
        if s is not None:
            ser = s
            ser_port = port
            ser_baud = baud
            return

    print "NO FIRMWARE RESPONSE on any port/baud"
    connectFallback( ports )

def reconnect():
    global ser
    try:
        if ser is not None:
            ser.close()
    except:
        pass
    ser = None
    connect()
    if ser is None:
        return
    #reopening the port resets the Arduino (DTR toggle): servos return to
    #raw zero and calibration is wiped. Wait for the reboot, then restore
    #the offsets so subsequent positions are correct again.
    #probePort already waited ~2.5s; short pause then restore calibration
    time.sleep(0.5)
    sendOffsets()

def utfy_dict2(dic):
    if isinstance(dic,unicode):
        return(dic.encode("utf-8"))
    elif isinstance(dic,dict):
        for key in dic:
            dic[key] = utfy_dict2(dic[key])
        return(dic)
    elif isinstance(dic,list):
        new_l = []
        for e in dic:
            new_l.append(utfy_dict2(e))
        return(new_l)
    else:
        return(dic)

def dictFromJsonFile2( filename ):
    jdata = {}
    try:
        with open( filename, "rb" ) as f:
            jdata = utfy_dict2( json.load(f))
            return jdata
    except Exception as e:
        #nothing
        print "couldnt open file"
    return False

#send offsets before positioning so positions are correct
#also called after every reconnect, since the Arduino reset wipes them
def sendOffsets():
    if ( not os.path.isfile( "offsets.json" ) ):
        return
    print( "opening offsets.json" )
    data = dictFromJsonFile2( 'offsets.json' )
    if ( data ):
        ocmd = "e:" + data["offsets"] 
        #ocmd = "e:" + "6,10,-60,15,0,-41,20,8,68,14,-4,81"
        print( "Sending " + ocmd )
        try:
            #raw writes on purpose: send() calls reconnect() which calls us,
            #and we must not recurse
            ser.write( ocmd + "\n" )
            time.sleep(0.1)
            ser.write( ocmd + "\n" )
        except:
            print "Could not send offsets"

def offsetsAllZero():
    data = dictFromJsonFile2( 'offsets.json' )
    if ( not data ):
        return True
    for v in data["offsets"].split( "," ):
        try:
            if float( v ) != 0:
                return False
        except:
            pass
    return True

#read one info line directly (only call while holding the command lock)
def readInfoLine():
    try:
        ser.flushInput()
        ser.write( "i\n" )
        for n in range( 4 ):
            line = ser.readline().rstrip()
            if line.startswith( "info" ):
                return line
    except:
        pass
    return ""

#this dog's IMU appears dead; balance mode (default on at 'go') freezes
#the motion engine so sit/stand/w poses are ignored. Match the webpage's
#balanceOff() and disable balance ONCE after each successful go.
#Do NOT spam A/N before every command: these letters may toggle or
#persist more firmware state than "balance off", and repeated sends are
#suspected of leaving the firmware in a bad saved state.
def disableBalanceAfterGo():
    #the firmware appears to EAT commands sent during the go stand-up
    #transition. In the serial test that worked, A/N went out ~10s after
    #go. Wait for the transition to finish, then disable balance, then
    #give the firmware a beat before queued pose commands flow through.
    #(we hold the command lock, so webpage presses queue behind this)
    time.sleep( 3.5 )
    try:
        ser.write( "A\n" )
        ser.write( "N\n" )
        print "balance disabled after go (dead IMU freezes poses otherwise)"
    except:
        print "could not disable balance after go"
    time.sleep( 0.5 )

#the firmware wedges permanently (until power cycle) if 'go' arrives
#before its calibration offsets are registered. Verify the offsets took
#effect (joint targets in the info line become non-zero) before sending
#'go'. If we cannot verify, refuse: a dog that ignores 'go' is annoying,
#a wedged dog is dead until someone flips the switch.
def safeGo():
    if ( offsetsAllZero() ):
        #cannot verify against all-zero calibration; send and hope
        print "go: offsets are all zero, sending go unverified"
        try:
            ser.write( "go\n" )
            print "go sent (unverified)"
            disableBalanceAfterGo()
        except:
            print "go dropped (serial error)"
        return
    for attempt in range( 3 ):
        sendOffsets()
        time.sleep( 0.3 )
        line = readInfoLine()
        pieces = line.split( "," )
        if ( len(pieces) >= 16 ):
            try:
                vals = [ float(x) for x in pieces[4:16] ]
            except:
                vals = []
            if ( any( v != 0 for v in vals ) ):
                try:
                    ser.write( "go\n" )
                    print "go sent (offsets verified)"
                    disableBalanceAfterGo()
                except:
                    print "go dropped (serial error)"
                return
        print "go: offsets not registered yet (info: " + line + "), retrying"
        time.sleep( 0.5 )
    print "REFUSING to send go: firmware never registered offsets."
    print "Sending go now would wedge it until a power cycle."
    print "Power-cycle the dog, wait 5s, then try again."

connect()
time.sleep(2)
#prime the serial connection
sendCommand( "noop" )
sendCommand( "noop" )
sendCommand( "noop" )
sendCommand( "noop" )
time.sleep(0.5)
sendOffsets()


#was referenced by the stop/quit handlers but never defined,
#so every stop command used to die with a NameError
def stop():
    send( "stop\n" ) #firmware command that halts motion

def getXYZPos( infostr ):
    xyzpos = ""
    pieces = infostr.split( ",")
    if (len(pieces) < 16 ):
            return None
    try:
        for l in range( 4, 16, 3 ):
            xyz = calcPositionXYZ( float(pieces[l]), float(pieces[l+1]), float(pieces[l+2]) )
            xyzpos += str(round(xyz[0])) + "," + str(round(xyz[1])) + "," + str(round(xyz[2])) + ","
    except:
        #serial reads time out at 0.1s and can return a partial/garbled
        #line; treat it as "no position available" instead of crashing
        return None
    return xyzpos.rstrip(",")


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
    global pub
    global ser
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
            stop()
        if ( cmd["command"] == "exit" or cmd["command"] == "quit" ):
            send( "off\n" ) #turn arm power off
            rospy.signal_shutdown("Shutting down" )
            sys.exit()

lock = threading.Lock()

def processCommand( str_ ):
    #cmd = str_
    #cmd = str_[:len(str_)-1]
    if('?' in str_):
        cmd = str_[:len(str_)-1]
    else:
        cmd = str_#[:len(str_)-1]
    # piece = str_
    # print  "pieces: " +  piece
    # if piece == "":
    #     return ""
    # if "," in piece or ":" in piece:
    #     if "a" in piece or "h" in piece or "k" in piece:
    #         cmd += "l:"
    #     elif "z" in piece or "x" in piece or "y" in piece:
    #         cmd += "g:"

    #     if "fl" in piece:
    #         cmd += "0,"
    #     elif "fr" in piece:
    #         cmd += "2,"
    #     elif "bl" in piece:
    #         cmd += "1,"
    #     elif "br" in piece:
    #         cmd += "3,"
    #     for value in piece.split(","):
    #         semicolon = value.find( ':' )
    #         if semicolon >= -1: #found
    #             val = value[(semicolon+1): ]
    #             # print val
    #             cmd += val + ","
    # else:
    #     cmd = piece
    # cmd = cmd.rstrip()
    # cmd = cmd.rstrip(",")
    print cmd
    #sendCommand(cmd.encode('utf-8'))
    return cmd

def listener(ros_data):
    global positions
    #global roscmd
    global dist
    global ser
    global prevchar
    global prevtime
    global prevpos
    global repeat_count
    global incr
    global power
    global error_in_last_sequence

    #print "Current threadid: ", threading.current_thread().ident
    inp = -1
    #print ros_data.data
    try:
        roscmd = json.loads(ros_data.data)
    except:
        print "Syntax error in " + ros_data.data
        return
    lock.acquire()
    #the try/finally is critical: rospy swallows exceptions raised in
    #callbacks, so without it a single error here would leave the lock
    #held forever and every future command (web or terminal) would hang
    try:
        if( roscmd.has_key('command') ):
            cmd = copy.deepcopy( roscmd )
            roscmd = {}
            #print json.dumps(cmd)
            if( cmd["command"] == "direct" ):
                cmdcmd = processCommand( cmd["v1"] )
                print cmdcmd
                if ( cmdcmd == "i" ):
                       inp = 'i'
                elif ( cmdcmd == "k" ):
                        inp = 'k'
                elif ( cmdcmd == "u" ):
                        inp = 'u'
                elif ( cmdcmd != "" ):
                    print "Sending ", cmdcmd
                    send( cmdcmd.encode('utf-8') + "\n" )
            elif ( cmd["command"] == "action" ):
                inp = cmd["v1"]
            elif ( cmd["command"] == "sequence" ):
                if ( not evosequence.runSequenceFile( cmd["v1"], processCommand, sendCommand, False) ): #check keyboard
                    #publish message so user knows of error
                    print "Error while running sequence"
                    error_in_last_sequence = True
            elif ( cmd["command"] == "apenableshutdown" ):
                    os.system("/etc/accesspoint_enable_shutdown.sh")
            elif ( cmd["command"] == "apdisableshutdown" ):
                    os.system("/etc/accesspoint_disable_shutdown.sh")

            if ( inp == "setastall" ):
                try:
                    print( "Sending u" )
                    sendCommand( "u" )  #get actual servo positions
                    apos = ser.readline().rstrip()
                    if ( not apos.startswith( "apos," ) ):
                        apos = ser.readline().rstrip()
                    if ( not apos.startswith( "apos," ) ):
                        apos = ser.readline().rstrip()
                    if (apos.startswith( "apos," ) and len(apos) > 10 ):
                        positions = apos.split(",")
                        positions.pop(0)
                        positions.pop(0)
                        offsets = ','.join( positions )
                        print("Sending " + "e:" + offsets )
                        sendCommand( "e:"+offsets )
                        #save to file for next boot
                        j = { "offsets": offsets }
                        with open( "offsets.json", 'w' ) as outfile:
                            json.dump( j, outfile, ensure_ascii=True )
                except:
                    print "setastall failed (serial error)"


            if( inp == ord('q') or inp == 'q'):
                stop()
            elif( inp == "quit" or inp == "exit" ):
                stop()
                rospy.signal_shutdown("Shutting down" )
                sys.exit()
            elif( inp != -1 ):
                if (inp == 'k' ):
                    try:
                        sendCommand( "i" ) 
                        str_ = ser.readline().rstrip()
                        if (len(str_) > 10 and str_.startswith( "info" ) ):
                            xyzpos = getXYZPos( str_ )
                            #print( xyzpos )
                            sendCommand( "u" )  #get actual servo positions
                            apos = ser.readline().rstrip()
                            if ( not apos.startswith( "apos," ) ):
                                apos = ser.readline().rstrip()
                            if ( not apos.startswith( "apos," ) ):
                                apos = ser.readline().rstrip()
                            if ( not apos.startswith( "apos," ) ):
                                apos = ser.readline().rstrip()
                            if ( apos.startswith( "apos," ) ):
                                j = {"pos": str_, "xyz": xyzpos, "apos": apos } 
                            else:
                                j = {"pos": str_, "xyz": xyzpos } 
                            pub.publish( String( json.dumps( j ) ) )
                    except:
                        #skip this status poll; next one runs in 0.2s
                        print "Status poll failed (serial error)"
                elif(inp == 'updateFirmware'):
                    print( "Updating Firmware" )
                    os.system('./update_arduino.sh')
                elif(inp.lower() == 'xs' or inp.lower() == 'fx' or inp.lower() == 'fy' or inp.lower() == 'bx' or inp.lower() == 'by' or inp.lower() == 'rr' or inp.lower() == 'rl' or inp.lower() == 't'):
                    sendCommand("o," + inp)


    finally:
        lock.release()

rospy.init_node("myListener")
rospy.Subscriber("/evocar/pub", String, listener, queue_size=5)
rospy.Subscriber("/evocar/system", String, sysListener, queue_size=5)
pub = rospy.Publisher('/evocar/status', String, queue_size=5)
selfpub = rospy.Publisher('/evocar/pub', String, queue_size=5)
print "evodogduino running"
t = threading.Thread(target=infothread, name="info")
t.daemon = True
t.start()
rospy.spin()
quitted = True

#Turn evodog power off
send( "off\n" )

