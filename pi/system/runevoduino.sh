#!/bin/bash
source /opt/ros/melodic/setup.bash
export PYTHONPATH="/opt/ros/melodic/lib/python2.7/dist-packages:/usr/lib/python2.7/dist-packages"
. $HOME/.bashrc
export ROS_MASTER_URI=`cat $HOME/ros_master.txt`
cd /home/pi/system
# -u = unbuffered output so prints show up live in journalctl
/usr/bin/python -u /home/pi/system/evodogduino.py
