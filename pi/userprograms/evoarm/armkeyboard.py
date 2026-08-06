import serial
import time
import getch
import sys
from termios import tcflush, TCIOFLUSH
import math
import os
import rospy
import json
import copy
from std_msgs.msg import String
from ReadLine import ReadLine


rospy.init_node("evoarmkeyboard")
pub = rospy.Publisher('/evocar/pub', String, queue_size=5)
pubsys = rospy.Publisher('/evocar/system', String, queue_size=5)
time.sleep(0.1)
for i in range(10):
    pub.publish(String('{"command":"direct","v1":"ignore"}'))
    time.sleep(0.1)

prevseq = ""
def askAndRunSequence():
    global prevseq
    seq = raw_input( "Enter sequence filename without the .py: " )
    if ( seq != "" and seq != "q" ):
        if ( seq == "repeat" ):
            seq = prevseq
        else:
            prevseq = seq
        print "Press space to stop execution"
        #send command to run sequence
        pub.publish(String('{"command":"sequence","v1":"'+seq+'"}'))


print "Press q to quit anytime. "
print '''Keytrokes: 
  a to f: increment position of joints a through f
  A to F: decrement position of joints a through f
  x/X: move gripper farther or closer without changing orientation
  y/Y: move gripper up or down without changing orientation
  j: go into command mode, lets type full commands
  i: print current arm configuration
  s: run a sequence. prompts for sequence filename
'''
quitted = False
joystickMode = True
prevchar = ' '
prevtime = 0
prevpos = {}
repeat_count = 0

def sendStop():
    pubsys.publish(String('{"command":"stop"}' )) 

if len(sys.argv) > 1:
    arg = 1
    while arg < len(sys.argv):
        if sys.argv[arg] == "-s" and len(sys.argv) > (arg+1):
            time.sleep(1)
            arg += 1
            pub.publish(String('{"command":"sequence","v1":"'+sys.argv[arg]+'"}'))
        arg += 1

    
while True and not quitted:
    if( not joystickMode ):
        inp = raw_input( "Input: " )
        if( inp == "-1" or inp == "q" or inp == "Q" or
            inp == "quit" or inp == "exit" ):
            sendStop()
            if ( inp == "exit" or inp == "quit" ):
                pubsys.publish(String('{"command":"exit"}' )) #cause listener to exit
            break;
        if( inp != "" ):
            if inp == "s": # sequence
                askAndRunSequence()
            elif ( inp == "j" ):
                joystickMode = True
                print "Joystick Mode: ON"
            elif ( inp == " " ):
                sendStop()
            else:
                #send full command
                pub.publish(String('{"command":"direct","v1":"'+inp+'"}'))
            inp = ""


    if(joystickMode):
        char = getch.getch()
        tcflush(sys.stdin, TCIOFLUSH) #discard built up keystrokes
        print char +  " pressed "
        if ( char == 'j' ):
            joystickMode = False
            print "Joystick Mode: OFF"
            char = ' '
        elif char == 's':
            askAndRunSequence()
        else:
            #send keyboard command
            pub.publish(String('{"command":"action","v1":"'+char+'"}'))

        #additionally
        if char == ' ':
            sendStop()
            
        if char == 'q':
            break

sendStop()
