E-Stop USB conversion project

This project is a custom made conversion kit for an Eaton E-Stop to allow it to send a
	keystroke over USB (ESC by default) to trigger execution of a program to halt.

Hardware:	
	The hardware modifications were fairly nonintrusive. I replaced the XLR plug and socket with a
	blank on one side and a carrier for an Adafruit Qt Py 2040 for the other side which exposes
	the USB port. The carrier also has a provision for a small protoboard which was used to
	simplify the wiring to the E-Stop button and lockout key cylinder. The protoboard also
	positions the ready and start LEDs in the correct position and contains their driver
	circuitry.
	
	The CAD was done in SolidEdge, the plug and carrier were FDM 3D printed

Electrical:	
	Unfortunately, I built the circuitry on the protoboard on the spot without schematics, so there
	is no documentation for that. It was very simple though: just some current limiting resistors
	for hot side of the button and key barrel (in case of a short), current limiting resistors for
	the LEDs, and a couple NFETs to drive the LEDs.
	
	The circuits for the switches are independant from each other, so the key cylinder can be
	disabled in software. The start button was left unconnected.

Software:
	Written for CircuitPython running on an Adafruit Qt Py 2040. Utilizes Adafruit keyboard libraries

	The software monitors E-Stop position and lock cylinder position. The start button is not monitored
	When E-Stop is down or the lock cylinder is set to the lock position, ESC keypress will be
	sent to the host every 5 seconds and the ready LED will blink rapidly.
		Whenever the ESC key is down, the start LED will be lit
	When the E-Stop is up or the lock cylinder is unlocked, the ready LED will be lit
	
	Implemented using a simple state machine. Every loop looks at the state variables and determines
	what state the system is in, and handles state transitions if need be.
	
	Utilizes timestamps and calculated delta times to determine when to transition between states.
	This was done to prevent sleep calls which block execution, which would result in unacceptable
	latency on E-Stop activation or deactivation.