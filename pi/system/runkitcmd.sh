#!/bin/bash
KIT=$1
shift
cd kits/$KIT
CMD="./$KIT.sh $@"
echo $CMD
$CMD
