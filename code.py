##################################################################################################
# E-Stop USB Program by Kenneth Lopez
# Version 2.0.1, 7/16/24
#
# Monitors E-Stop position and lock cylinder position. The start button is not monitored
#	When E-Stop is down or the lock cylinder is set to the lock position, ESC keypress will be
#	sent to the host every 5 seconds and the ready LED will blink rapidly.
#		Whenever the ESC key is down, the start LED will be lit
#	When the E-Stop is up or the lock cylinder is unlocked, the ready LED will be lit
#
# Written to run on Adafruit Qt Py 2040. Utilizes Adafruit keyboard libraries
#
#
#    Copyright (C) 2024  Kenneth Lopez (lopezk38@gmail.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#
##################################################################################################

##################################################################################################
# Imports
##################################################################################################

import time

import board
import digitalio

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode


##################################################################################################
# Settings
##################################################################################################

DEBUG = False

#Should the key cylinder be disabled/ignored?
DISABLE_KEYCYL = True

#Should all lights be disabled?
DISABLE_LEDS = False

#Should LEDS only run while the E-Stop is triggered? DISABLE_LEDS will override this setting
FLASHING_LEDS_ONLY = False

#The key to send while the E-Stop is triggered
KEYCODE = Keycode.ESCAPE

#How long to wait in between keypresses while the E-Stop is triggered
DELAY = 5 #seconds

#How long to hold the key down for during a keypress
#Must be less than DELAY or program behavior will be undefined
DWELL = 0.25 #seconds

#How long to hold the ready LED on or off for while flashing
FLASHTIME = 0.25 #seconds. This is equal to 1/2 the frequency period, so 0.5 seconds == 1 Hz


##################################################################################################
# Pin definitions
##################################################################################################

class Pins():
    #Set pin objects to simple names
    ESTOP = digitalio.DigitalInOut(board.RX)
    KEYCYL = digitalio.DigitalInOut(board.MISO)
    LED_START = digitalio.DigitalInOut(board.SDA)
    LED_READY = digitalio.DigitalInOut(board.TX)
    
    #Constructor
    def __init__(self):
        #Configure pin objects
        #ESTOP
        self.ESTOP.direction = digitalio.Direction.INPUT
        self.ESTOP.pull = digitalio.Pull.DOWN
        
        #KEYCYL
        self.KEYCYL.direction = digitalio.Direction.INPUT
        self.KEYCYL.pull = digitalio.Pull.DOWN
        
        #LED_START
        self.LED_START.direction = digitalio.Direction.OUTPUT
        
        #LED_READY
        self.LED_READY.direction = digitalio.Direction.OUTPUT
        
        #Set initial LED states. Off if DISABLE_LEDS or FLASHING_LEDS_ONLY is true, On if false
        self.LED_START.value = not (DISABLE_LEDS or FLASHING_LEDS_ONLY)
        self.LED_READY.value = not (DISABLE_LEDS or FLASHING_LEDS_ONLY)
        
    @staticmethod
    def togglePin(pin):
        if (DISABLE_LEDS):
            #LEDs are disabled, always set state to false (off)
            pin.value = False
            
        else:
            #XOR current state to find it's complement
            pin.value = pin.value ^ True
       
    @staticmethod
    def setPin(pin, state):
        if (DISABLE_LEDS or FLASHING_LEDS_ONLY):
            #LEDs are disabled, always set state to false (off)
            pin.value = False
            
        else:
            pin.value = state
        
    #String override
    def __str__(self):
        return ("ESTOP: " + str(self.ESTOP.value) + "\n"
                + "KEYCYL: " + str(self.KEYCYL.value) + "\n"
                + "LED_START: " + str(self.LED_START.value) + "\n"
                + "LED_READY: " + str(self.LED_READY.value))


##################################################################################################
# State class
##################################################################################################
    
class State():
    active = False
    keyDown = False
    
    timeActivated = -100 #Seconds since boot
    timeLastFlashed = -100 #Seconds since boot
    timeLastKeypress = -100 #Seconds since boot
    
    #String override
    def __str__(self):
        return ("active: " + str(self.active) + "\n"
                + "keyDown: " + str(self.keyDown) + "\n"
                + "timeActivated: " + str(self.timeActivated) + "\n"
                + "timeLastFlashed: " + str(self.timeLastFlashed) + "\n"
                + "timeLastKeypress: " + str(self.timeLastKeypress))


##################################################################################################
# Init
##################################################################################################

#Init Pin IO
pins = Pins()

#Spawn Keyboard object
keyboard = Keyboard(usb_hid.devices)

#Spawn State object
state = State()


##################################################################################################
# Main loop
##################################################################################################

def main():
    while True: #loop forever
        dbg_printIOState()
        
        #Check if the E-Stop is active
        if (checkStops()):
            #Is triggered
            
            #Were we already active?
            if (state.active):
                #We were already active
                
                #Is the escape key down/pressed?
                if (state.keyDown):
                    #Key is down
                    #Is it time to release the key?
                    if ((time.monotonic() - state.timeLastKeypress >= DWELL)):
                        #DWELL time has been exceeded, time to release
                        releaseKeyPress()
                    
                else:
                    #Key is up/unpressed
                    #Has it been longer than 5 seconds since the last sent keypress?
                    if ((time.monotonic() - state.timeLastKeypress) >= DELAY):
                        #It has been longer, send a keypress
                        sendKeyPress()
                
                #Blink the start LED rapidly
                if ((time.monotonic() - state.timeLastFlashed) >= FLASHTIME):
                    #It has been longer than half the period of the given frequency, time to toggle
                    pins.togglePin(pins.LED_READY)
                    state.timeLastFlashed = time.monotonic()
                
            else:
                #We were not active, handle state transition
                state.active = True
                state.timeActivated = time.monotonic()
                state.timeLastKeypress = -100 #Reset this timer on state entry to guarantee rapid
                                               #keypress on E-Stop hit if the E-Stop was very
                                               #recently deactivated
                
        else:
            #Is not triggered
            
            #Were we already inactive?
            if (state.active):
                #We were active, handle state transition
                state.active = False
                pins.setPin(pins.LED_READY, True) #Turn on the ready LED
                pins.setPin(pins.LED_START, False) #Make sure the start LED is off
                releaseKeyPress() #Handle edge case where transition occurs during dwell time
                
            #else: do nothing since we were already inactive
                
        time.sleep(0.01) #Wait 0.01 seconds before looping to allow inputs to debounce


##################################################################################################
# Function definitions
##################################################################################################

##################################################################################################
# checkStops()
#
# Checks if the E-Stop has been triggered either through the big red button or the lock cylinder
#   If DISABLE_KEYCYL is true, only the button will be checked, the key cylinder will be ignored
#
# Returns true if the E-Stop has been triggered, false if not
##################################################################################################
def checkStops():
    #Check if the button is down or the cylinder is locked
    #Input signals are backwards from what you would think. A true input is not triggered
    if pins.ESTOP.value and (pins.KEYCYL.value or DISABLE_KEYCYL):
        return False #Return not triggered
    
    else:
        return True #Return triggered

##################################################################################################
# sendKeyPress()
#
# Sends the escape keypress (or another key if KEYCODE has been changed in the constants section)
# Turns off the start LED
# Records when the key was pressed, sets the keyDown state
#
# Returns void
##################################################################################################
def sendKeyPress():
    #Press the key, turn off the start LED
    keyboard.press(KEYCODE)
    pins.setPin(pins.LED_START, False)
    
    #Update state record
    state.keyDown = True
    state.timeLastKeypress = time.monotonic()

##################################################################################################
# releaseKeyPress()
#
# Releases all keys and turns on the start LED, clears the keyDown state
#
# Returns void
##################################################################################################
def releaseKeyPress(): 
    #Release the key, update state record, relight the start LED
    keyboard.release_all()
    state.keyDown = False
    pins.setPin(pins.LED_START, True)

##################################################################################################
# dbg_printIOState()
#
# Prints the current position of all inputs and state of all outputs to shell
#
# Runs only if DEBUG is true
#
# Returns void
##################################################################################################
def dbg_printIOState():
    #Run only in debug mode
    if not DEBUG: return
    
    #Print every pin's state and all other state variables
    print(str(time.monotonic()) + "\n" + str(pins) + "\n" + str(state) + "\n")


#Call entry point
main()