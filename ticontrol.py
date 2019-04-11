"""
TiMotion Controller 

Supports TC15 V1 Controller (Without PS Features)
"""
import time
import threading
import zmq
import os
import sys
import serial
import logging

print("TiMotion Controller")
time.sleep(1)


if sys.platform == "win32":
    logging.critical("Win32 is an unsupported Platform")
    os.abort()
os.system('clear')
    
class TICONTROL(object):
    def __init__(self):
        self.up = bytearray([0xD8, 0xD8, 0xff, 0x02, 0x02])
        self.down = bytearray([0xD8, 0xD8, 0xff, 0x01, 0x01])
        self.reset = bytearray([0xD8, 0xD8, 0xff, 0x03, 0x03])
        try:
            self.port = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1)
        except:
            logging.critical('Failed to initialize Serial Port')

ticontrol = TICONTROL()

class ReadSerial(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.currentheight = int
        self.active = True
       
    def run(self):
        while self.active:
            try:
                raw_input = ticontrol.port.read(13)
            except:
                logging.warning('Cannot Read Serial Port!')
            toHex = lambda x: "".join("{:02X}".format(c) for c in x)
            line = (toHex(raw_input))
            seperate = ([line[i:i+2] for i in range(0, len(line), 2)])
            listnow = list(seperate)
            self.currentheight = int(listnow[11], 16)
            time.sleep(.01)
         
readserial = ReadSerial()

class ControlWorker(threading.Thread):
    def __init__(self, command):
        threading.Thread.__init__(self)
        self.command = command
        self.offset = int

    def run(self):
        if self.command == "reset":
            self.run_reset()
            return
        self.setheight = int(self.command)
        if self.setheight == readserial.currentheight:
            logging.warning('Desk is already at this height!')
        #Calculate Offset
        self.offset = readserial.currentheight - self.setheight
        if -7 <= self.offset <= 0:
            self.moveoffset("up", self.offset)
        if 0 <= self.offset <= 7:
            self.moveoffset("down", self.offset)
        #Continue if not offset motion
        if self.setheight < readserial.currentheight:
            self.setheight = self.setheight + 5
        if self.setheight > readserial.currentheight:
            self.setheight = self.setheight - 5
        self.move(self.setheight)        

    def moveoffset(self, direction, offset):
        if direction == "up":
            if offset == -1:
                self.offseterror()
            if offset == -2:
                for x in range(1):
                    ticontrol.port.write(ticontrol.up)
                logging.warning('Offset Motion Complete')
            if offset == -3:
                self.offseterror()
            if offset == -4:
                for x in range(2):
                    ticontrol.port.write(ticontrol.up)
                    time.sleep(.5)
                logging.warning('Offset Motion Complete')
            if offset == -5:
                self.offseterror()
            if offset == -6:
                for x in range(3):
                    ticontrol.port.write(ticontrol.up)
                    time.sleep(.5)
                logging.warning('Offset Motion Complete')
        if direction == "down":
            if offset == 1:
                self.offseterror()
            if offset == 2:
                for x in range(1):
                    ticontrol.port.write(ticontrol.down)
                logging.warning('Offset Motion Complete')
            if offset == 3:
                self.offseterror()
            if offset == 4:
                for x in range(2):
                    ticontrol.port.write(ticontrol.down)
                    time.sleep(.5)
                logging.warning('Offset Motion Complete')
            if offset == 5:
                self.offseterror()
            if offset == 6:
                for x in range(3):
                    ticontrol.port.write(ticontrol.down)
                    time.sleep(.5)
                logging.warning('Offset Motion Complete')

    def offseterror(self):
        logging.warning('Offset Error')

    def move(self, setheight):
        time_started = time.time()
        seconds = 30
        while True:
            if time.time() > time_started + seconds:
                logging.warning('Control Worker failed to complete task in 30 seconds')
                break
            if readserial.currentheight == 0:
                break
            elif readserial.currentheight == self.setheight:
                logging.warning('Task Complete')
                time.sleep(2)
                break
            else:
                if readserial.currentheight > self.setheight:
                    ticontrol.port.write(ticontrol.down)
                    time.sleep(.2)
                if readserial.currentheight < self.setheight:
                    ticontrol.port.write(ticontrol.up)
                    time.sleep(.2)

    def run_reset(self):
        while True:
                ticontrol.port.write(ticontrol.reset)
                if readserial.currentheight == 255:
                    break 
        while True:
            ticontrol.port.write(ticontrol.reset)
            if 60 <= readserial.currentheight <= 70:
                       logging.warning('Desk reset successful')
                       break

    def force_reset(self):
        x = 0
        while True:
                ticontrol.port.write(ticontrol.reset)
                x += 1
                if x == 30:
                    break    

controlworker = None

class Server():
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:5500")
        self.socket.setsockopt(zmq.LINGER, 0)
        try: 
            self.command = None
        except:
            logging.warning("Failed to initialize socket")
            sys.exit()

    def listen(self):
        while True:
            self.command = self.socket.recv()
            print('Recieved Request:', (self.command))
            self.command = self.command.decode()
            if self.command == "height":
                self.socket.send(str(readserial.currentheight).encode())
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
                    if controlworker.isAlive() is False:
                        readserial.active = True
                        controlworker = ControlWorker(self.command) 
                        controlworker.setDaemon(True)
                        controlworker.start()
                    else:  
                        logging.warning("Control Worker Busy")
                except Exception as error:
                    readserial.active = True
                    controlworker = ControlWorker(self.command) 
                    controlworker.setDaemon(True)
                    controlworker.start()
            else:
                self.socket.send(b"invalid_arg")

if __name__ == '__main__':
    readserial.setDaemon(True)
    readserial.start()
    server = Server()
    server.listen()
