#!/bin/bash
source /opt/ros/melodic/setup.bash
export PYTHONPATH="/opt/ros/melodic/lib/python2.7/dist-packages:/usr/lib/python2.7/dist-packages"
. $HOME/.bashrc
export ROS_MASTER_URI=`cat $HOME/ros_master.txt`
cd /home/pi/system
MYFILE=evocarnew
if [ -f "$MYFILE" ]; then
	mv evocar evocar-prev
	mv $MYFILE evocar
	chmod +x evocar
fi
/home/pi/system/evocar
