#!/usr/bin/python

import RPi.GPIO as GPIO
import os
import time

gpio_button_pin = 3
gpio_led_pin = 17

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
#Use BCM pin numbering (i.e. the GPIO number, not pin number)
#WARNING: this will change between Pi versions
#Check yours first and adjust accordingly

GPIO.setup(gpio_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP )
GPIO.setup(gpio_led_pin, GPIO.OUT )
GPIO.output(gpio_led_pin, GPIO.LOW)
#It's very important the pin is an input to avoid short-circuits
#The pull-up resistor means the pin is high by default
done = False
while not done:
    GPIO.wait_for_edge(gpio_button_pin, GPIO.FALLING)
    #Use falling edge detection to see if pin is pulled 
    #low to avoid repeated polling
    #only trigger if pressed for one second or more
    if GPIO.wait_for_edge(gpio_button_pin, GPIO.RISING, timeout = 1500 ) is None:
        done = True
        #print( "button pressed for 2 seconds" )
        GPIO.output(gpio_led_pin, GPIO.HIGH)
        time.sleep(1)
        os.system("sudo shutdown -h now")
        #Send command to system to shutdown

#GPIO.cleanup()
#Revert all GPIO pins to their normal states (i.e. input = safe)

