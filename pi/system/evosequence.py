import time
import sys
from termios import tcflush, TCIOFLUSH
import math
import json
import os
import os.path
from importlib import import_module
if os.name == 'nt':
    import msvcrt
else:
    import sys, select

cancel = False

def kbhit():
    ''' Returns True if a keypress is waiting to be read in stdin, False otherwise.
    '''
    if os.name == 'nt':
        return msvcrt.kbhit()
    else:
        dr,dw,de = select.select([sys.stdin], [], [], 0)
        return dr != []

def utfy_dict(dic):
    if isinstance(dic,unicode):
        return(dic.encode("utf-8"))
    elif isinstance(dic,dict):
        for key in dic:
            dic[key] = utfy_dict(dic[key])
        return(dic)
    elif isinstance(dic,list):
        new_l = []
        for e in dic:
            new_l.append(utfy_dict(e))
        return(new_l)
    else:
        return(dic)

def dictFromJsonFile( filename ):
    jdata = {}
    try:
        with open( filename, "rb" ) as f:
            jdata = utfy_dict( json.load(f))
            return jdata
    except Exception as e:
        #nothing
        print "couldnt open file"
    return False
    
def runSequence( seq, processCommand, sendCommand, checkkb ): #callback
    global cancel
    last_command = ""
    saved_positions = dictFromJsonFile( "../userprograms/savedpositions.json" )
    for dict in seq:
        cmdstr = dict["command"]
        last_command = cmdstr
        if last_command == "loop" or last_command == "exit":
            break;
        if "type" in dict and dict["type"] == "seq":
            runSequenceFile( cmdstr, processCommand, sendCommand, checkkb )
            if ( cancel  ):
                print "Remaining sequence cancelled"
                return False
            continue
        duration = 1000
        if "delay" in dict and dict["delay"] != "":
                duration = int(float(dict["delay"]) * 1000)
        if "type" in dict and dict["type"] == "posname":
            cmdstr = saved_positions[cmdstr]
            cmdstr = 'w,'+str(duration)+',' + cmdstr
        if "type" in dict and dict["type"] == "pos":
            #cmdstr is already the desired position
            cmdstr = 'w,'+str(duration)+',' + cmdstr
        if "type" in dict and dict["type"] == "action":
            cmdstr = cmdstr
        if "type" in dict and dict["type"] == "control":
            if cmdstr == "pwr=on":
                cmdstr = "on"
            elif cmdstr == "pwr=off":
                cmdstr = "off"

        # prefix the speed instead of suffixing it, was bug before
        # RG Nov 27, 2020
        if "speed" in dict and dict["speed"] != "":
            print "Sending speed"
            sendCommand("s:" + ( "%0.3f" % float(dict["speed"]) ))
        cmd = processCommand( cmdstr )
        if ( cmd != "" ):
            print cmd
            sendCommand( cmd )
        time.sleep( float(dict[ "delay" ]) )
        if ( cancel or (checkkb and kbhit()) ):
            print "Remaining sequence cancelled"
            return False
    return last_command == "loop"

def runSequenceFile( seqfile, processCommand, sendCommand, checkkb ): #callback fn
    global cancel
    if seqfile == "":
        return False
    if seqfile in sys.modules: #remove if previously loaded
        del sys.modules[seqfile]

    sys.path.append("../userprograms/apps")

    #first try as json
    data = {}
    try:
        with open( "../userprograms/apps/" + seqfile+".json", "rb" ) as f:
            data = utfy_dict( json.load(f))
            cancel = False
            while runSequence( data["sequence"], processCommand, sendCommand, checkkb ):
                continue; #means last line of sequence was "loop", to repeat
            return True
    except Exception as e:
        #nothing
        print e
        print "couldnt open file"

    pyseqfile = seqfile.replace( ".py", "" )
    if pyseqfile in sys.modules: #remove if previously loaded
        del sys.modules[pyseqfile]
    try:
        __import__( pyseqfile )
    except:
        print "Error opening ", pyseqfile
        return False
    #module = import_module( seqfile, "apps" )
    #module = import_module( "apps." + seqfile )
    #for m in sys.modules:
    #    print m
    module = sys.modules[ pyseqfile ] #'apps' isnt part of name
    cancel = False
    try:
        while runSequence( module.sequence, processCommand, sendCommand, checkkb ):
            continue; #means last line of sequence was "loop", to repeat
    except:
        return False

    return True

def cancelSequence():
    global cancel
    cancel = True
