#!/bin/bash

sudo systemctl start camera
echo "Position your face in front of the camera about 2 feet away"
echo "And press enter"
read WWW
echo "Running continous face detection on captured images"
echo "This might take 15-20 seconds to start doing something"
echo "Goto the arm's browser app and add /face.html at the end of the url"
python facedetect-cont.py
sudo systemctl stop camera
