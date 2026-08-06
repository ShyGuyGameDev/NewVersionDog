To generate single still image from camera,
make sure camera is off in your evoarm web-app

then run:
raspistill -w 640 -h 480 -o cam.jpg

check that the image was captured using
ls -l

then run
python facedetect.py

to see the result, goto your browser app
and add /output.jpg at the end of url



to do continuous detecton, start the camera in your web-app
then run
python facedetect-cont.py
or
python facedetect-follow.py

You can see the output images in the browser
just add "/face.html" at the end of your web-apps url in the browser
