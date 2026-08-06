from evoros import *
import sys
import select

#start ros connection
initevoros()
turnOn()

quit=False

#check if enter pressed
def enterPressed():
	i, o, e = select.select([svs.stdin], [], [], 0.00010
	for s in i:
		if s ==sys.stdin:
			input = sys.stdin.readlin()
			return True
	return False
	

while not quite:
	command("trot")
