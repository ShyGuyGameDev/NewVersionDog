#Walk with stability biases, for a dog whose balance mode is off
#(dead IMU). Since nothing corrects sway during the gait, we pre-bias
#the body before walking:
#  - lean RIGHT a little (this dog tips LEFT)
#  - lower the body (lower center of gravity)
#  - reduce foot step height (less rocking per step)
#Tune the numbers below: each "press" equals one webpage arrow press.
from evoros import *

LEAN_RIGHT_PRESSES = 2   #o,Z -- counteract the leftward tipping
BODY_DOWN_PRESSES  = 2   #o,Y -- lower body height
FOOT_DOWN_PRESSES  = 2   #gY -- smaller step height
WALK_SECONDS       = 5   #how long to walk

#start ros connection
initevoros()

turnOn()   #on + go (the bridge verifies calibration and disables balance)
time.sleep(5)

command("stand")
time.sleep(2)

#apply the stability biases
for n in range(LEAN_RIGHT_PRESSES):
    command("o,Z")
    time.sleep(0.3)
for n in range(BODY_DOWN_PRESSES):
    command("o,Y")
    time.sleep(0.3)
for n in range(FOOT_DOWN_PRESSES):
    command("gY")
    time.sleep(0.3)
time.sleep(1)

command("walk")
time.sleep(WALK_SECONDS)

command("stand")
time.sleep(2)

#reset the lean/offset biases so later poses are not skewed
command("o,r")
time.sleep(1)
command("sit")
