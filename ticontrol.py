"""
TiMotion Controller 

Supports TC15 V1 Controller
Note: This version doesn't work with V2 TC15 Controller with Power Saving Features
"""
import time
import threading
import zmq
import os
import sys
import serial
import logging

class TICONTROL(object):
    def __init__(self):
        self.up = bytearray([0xD8, 0xD8, 0xff, 0x02, 0x02])
        self.down = bytearray([0xD8, 0xD8, 0xff, 0x01, 0x01])
        self.reset = bytearray([0xD8, 0xD8, 0xff, 0x03, 0x03])
       
class Serial(threading.Thread):
    def __init__(self, port_id):
        threading.Thread.__init__(self)
        self.currentheight = int
        self.active = True
        try:
            self.port = serial.Serial(port_id, baudrate=9600, timeout=1)
        except:
            logging.critical('Failed to initialize Serial Port')
       
    def run(self):
        while self.active:
            try:
                raw_input = self.port.read(13)
            except:
                logging.warning('Cannot Read Serial Port!')
            toHex = lambda x: "".join("{:02X}".format(c) for c in x)
            line = (toHex(raw_input))
            seperate = ([line[i:i+2] for i in range(0, len(line), 2)])
            listnow = list(seperate)
            self.currentheight = int(listnow[11], 16)
            time.sleep(.01)

class ControlWorker(threading.Thread):
    def __init__(self, command):
        threading.Thread.__init__(self)
        self.command = command
        self.offset = int

    def run(self):
        if self.command == "reset":
            self.run_reset()
            return True
        if self.command == "force_reset":
            self.force_reset()
            return True
        try: 
            self.setheight = int(self.command)
        except Exception as E:
            logging.critical("An error occurred while processing the given request {1}".format(E))
        if self.setheight == serial.currentheight:
            logging.warning("Requested height is already set")
            return False
        if self.hasOffset(self.setheight):
            self.moveDeskWithOffset(self.offset)
        else:
            if self.setheight < serial.currentheight:
                self.setheight = self.setheight + 5
            if self.setheight > serial.currentheight:
                serial.port.write(ticontrol.up)
                self.setheight = self.setheight - 5
            self.moveDesk(self.setheight)        

    def hasOffset(self, setheight):
        self.offset = serial.currentheight - setheight
        if -7 <= self.offset <= 7:
            return True
        else:
            return False

    def moveDeskWithOffset(self, offset):
        num_of_serial_writes = int(abs(self.offset/2))
        if self.offset < 0:
            if abs(self.offset) % 2 == 0:
                for serial_write in range(num_of_serial_writes):            
                    serial.port.write(ticontrol.up)
            else:
                logging.warning('Offset value does not meet criteria')
        if self.offset > 0:
            if self.offset > 0:
                if abs(self.offset) % 2 != 0:
                    for serial_write in range(num_of_serial_writes):
                        serial.port.write(ticontrol.down)
                else:
                    logging.warning('Offset value does not meet criteria')

    def moveDesk(self, setheight):
        time_started = time.time()
        seconds = 30
        while True:
            if time.time() > time_started + seconds:
                logging.warning('Control Worker failed to complete task in 30 seconds')
                break
            if serial.currentheight == 0:
                logging.warning('Failed to Read Serial Port. Aborting...')
                break
            elif serial.currentheight == self.setheight:
                logging.warning('Task Complete')
                time.sleep(2)
                break
            else:
                if serial.currentheight > self.setheight:
                    serial.port.write(ticontrol.down)
                    time.sleep(.2)
                if serial.currentheight < self.setheight:
                    serial.port.write(ticontrol.up)
                    time.sleep(.2)

    def run_reset(self):
        """Resets the controller"""
        while True:
                serial.port.write(ticontrol.reset)
                if serial.currentheight == 255:
                    break 
        while True:
            serial.port.write(ticontrol.reset)
            if 60 <= serial.currentheight <= 70:
                       logging.warning('Desk reset successful')
                       break

    def force_reset(self):
        """Forces the controller to reset when not responding"""
        numSerialResetWrites = 30
        for serial_write in range(numSerialResetWrites):
                    serial.port.write(ticontrol.reset)
                    numSerialResetWrites += 1
                   
class Server():
    """Request/Recieve Server. Sends commands to controller"""
    def __init__(self):
        try:
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind("tcp://*:5500")
            self.socket.setsockopt(zmq.LINGER, 0)
        except:
            logging.warning("Failed to initialize socket")
            sys.exit()

    def listen(self):
        logging.info('Controller Ready')
        while True:
            self.command = self.socket.recv()
            logging.info('Recieved Request: {0}'.format(self.command))
            self.command = self.command.decode()
            if self.command == "height":
                self.socket.send(str(serial.currentheight).encode())
                return 
            if self.command == "reset":
                self.socket.send(b"Resetting")
                controlworker = ControlWorker(self.command) 
                controlworker.setDaemon(True)
                controlworker.start()
                continue
            if 65 <= int(self.command) <= 130:
                self.socket.send(b"Received")
                try:  
                    if not controlworker.isAlive():
                        serial.active = True
                        controlworker = ControlWorker(self.command) 
                        controlworker.setDaemon(True)
                        controlworker.start()
                    else:  
                        logging.warning("Control worker busy")
                except Exception as error:
                    serial.active = True
                    controlworker = ControlWorker(self.command) 
                    controlworker.setDaemon(True)
                    controlworker.start()
            else:
                self.socket.send(b"invalid argument")

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    serial = Serial("/dev/ttyS0")
    ticontrol = TICONTROL()
    controlworker = None
    serial.setDaemon(True)
    serial.start()
    server=Server()
    server.listen()

   


			
			