#!/bin/bash
MYIP=`ip route get 1 | sed -n 's/^.*src \([0-9.]*\) .*$/\1/p'`
if [ "X$MYIP" == "X" ]
then
    MYIP=`hostname -I`
fi
echo $MYIP
