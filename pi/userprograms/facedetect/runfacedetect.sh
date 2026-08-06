#!/bin/bash

echo "Position your face in front of the camera about 2 feet away"
echo "And wait at least 10 seconds after pressing enter"
sudo systemctl stop camera
read WWW
raspistill -w 640 -h 480 -o cam.jpg
echo "Running face detection on captured image"
echo "This might take around 10 to 15 seconds"
python facedetect.py
echo "Goto the arm's browser app and add /output.jpg at the end of the url"
echo "If you see a blue rectangle around your face, it worked!"

