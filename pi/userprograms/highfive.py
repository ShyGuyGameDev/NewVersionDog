from evoros import *

#start ros connection
initevoros()

turnOn()

# Improved high five (front-right paw):
# - no spaces in pose strings (firmware parser is picky)
# - weight-shift before lifting so the dog stays balanced
# - raise / tap / raise / tap, then settle and sit
# Joint order: FL, BL, FR, BR  (swivel, shoulder, elbow each)

command("stand")
time.sleep(0.6)

# Prep: shift weight, start lifting FR
goToBodyPos(500, "-9,33,64,-9,33,64,-9,39,73,-9,33,64")
time.sleep(0.4)
goToBodyPos(500, "-9,33,64,-9,33,64,-9,56,102,-9,33,64")
time.sleep(0.4)

# Raise paw
goToBodyPos(800, "-9,33,64,-9,33,64,-9,-21,112,-9,33,64")
time.sleep(0.9)

# High-five taps
goToBodyPos(600, "-9,33,64,-9,33,64,-9,-17,89,-9,33,64")
time.sleep(0.7)
goToBodyPos(600, "-9,33,64,-9,33,64,-9,-21,112,-9,33,64")
time.sleep(0.7)
goToBodyPos(600, "-9,33,64,-9,33,64,-9,-17,89,-9,33,64")
time.sleep(0.7)

# Settle and sit
goToBodyPos(600, "-9,33,64,-9,33,64,-9,-21,112,-9,33,64")
time.sleep(0.7)
goToBodyPos(500, "-9,33,64,-9,33,64,-9,56,102,-9,33,64")
time.sleep(0.4)
goToBodyPos(500, "-9,33,64,-9,33,64,-9,39,73,-9,33,64")
time.sleep(0.4)

command("sit")
time.sleep(0.5)
