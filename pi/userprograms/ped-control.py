import serial
import time
import getch
from curses import *
dist = ""
import atexit

def exit_handler():
    print 'Exiting!'

#atexit.register(exit_handler)

try:
    ser = serial.Serial('/dev/ttyUSB0', 500000, timeout = 0.1, write_timeout = 0.5 ) # Establish the connection on a specific port
except:
    ser = serial.Serial('/dev/ttyUSB1', 500000, timeout = 0.1, write_timeout = 0.5 ) # Establish the connection on a specific port

time.sleep(2)

def send ( string ):
    try:
        ser.write(string + "\n" )
    except:
        return


def stop():
    send("stop\n")

send( "stand" )
time.sleep( 1 )

cmd = raw_input( "type command: " )
while( cmd != "quit" and cmd != "exit" and cmd != "q" ):
    send( cmd )
    time.sleep( 0.1 )
    while ser.inWaiting():
            print ser.readline(),
    time.sleep( 0.1 )
    while ser.inWaiting():
            print ser.readline(),
    cmd = raw_input( "type command: " )
