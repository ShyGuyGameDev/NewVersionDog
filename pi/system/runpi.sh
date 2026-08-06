#!/bin/bash
source /opt/ros/melodic/setup.bash
export PYTHONPATH="/opt/ros/melodic/lib/python2.7/dist-packages:/usr/lib/python2.7/dist-packages"
. $HOME/.bashrc
export ROS_MASTER_URI=`cat $HOME/ros_master.txt`
echo $ROS_MASTER_URI
/opt/ros/melodic/bin/roscore 2>&1

