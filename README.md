An interface for mpu60 to use it as an inclinometer that is used in
geotechnical engineering, running inside a raspberry Pi 3, the basic idea is create a
GUI to interact with the mpu60 (Gyroscope, Accelerometer and temperature) module
and get the displacements with an initial position.

You need the following python 3 libraries.

- datetime
- smbus
- time
- math 
- csv
- os.path
- numpy
- matplotlib
- multiprocessing
- tkinter


To run this program you only need to write in your terminal:

"python3 inclinometer1.110.py"