import serial
import time
import getch
from curses import *
dist = ""
import atexit

def exit_handler():
    print 'Exiting!'

#atexit.register(exit_handler)


class ReadLine:
    def __init__(self, s):
        self.buf = bytearray()
        self.s = s

    def readline(self):
        i = self.buf.find(b"\n")
        if i >= 0:
            r = self.buf[:i+1]
            self.buf = self.buf[i+1:]
            return r
        i = max(0, min(2048, self.s.in_waiting))
        if (i == 0):
            return
        data = self.s.read(i)
        i = data.find(b"\n")
        if i >= 0:
            r = self.buf + data[:i+1]
            self.buf[0:] = data[i+1:]
            return r
        else:
            self.buf.extend(data)
            return




ser = serial.Serial('/dev/ttyUSB0', 500000, timeout = 0.1, write_timeout = 0.5 ) # Establish the connection on a specific port

#serialRead = ReadLine( ser )

time.sleep(2)

#serialRead = ReadLine( ser )

def send ( string ):
    
    try:
        ser.write(string + "\n" )
    except:
        return


def stop():
    send("stop\n")

send( "stand" )
time.sleep( 1 )
    
while( True ):
    raw_input( "press any key" )
    send( "on" )
    send( "go" )
    send( "s:3" )
    send( "sit" )
    time.sleep( 3 );
    send( "getup" )
    time.sleep( 2 );
#    send( "walk" )
#    time.sleep( 3 )
    send( "s:2" )
    send( "stand" )
    time.sleep( 1 )
    send( "s:1" )
    send( "look" )
    time.sleep( 2 )
    send( "stand" )
    time.sleep( 1 )
    send( "s:1.5" )
    send( "walk" )
    time.sleep( 5 )
    send( "stand" )
    time.sleep( 1 )
    send( "stop" )
    send( "s:1" )

