import threading
import zmq
import queue 
import logging

class deskclient(threading.Thread):
    def __init__(self, q, loop_time = 1.0/60):
        self.q = q
        self.timeout = loop_time
        super(deskclient, self).__init__()
        self.stop = False
        self.port = 5500
        self.is_idle = True
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)

    def onThread(self, function, *args, **kwargs):
        self.q.put((function, args, kwargs))

    def run(self):
        logging.debug('Starting Desk Service')
        print("Connecting to server...")
        self.socket.connect ("tcp://192.168.1.48:%s" % self.port)
        self.socket.setsockopt(zmq.LINGER, 0)
        while self.stop == False:
            try:
                function, args, kwargs = self.q.get(timeout=self.timeout)
                function(*args, **kwargs)
                if self.stop == True:
                    break
            except queue.Empty:
                self.idle()

    def idle(self):
        pass

    def sitDesk(self):
            command = '75'
            command = command.encode()
            try:
                self.socket.send(command)
                message = self.socket.recv()
            except Exception as error:
                print("Could not communicate with Desk Ctrl Process")
        
    def standDesk(self):
            command = '100'
            command = command.encode()
            try:    
                self.socket.send(command)
                message = self.socket.recv()
            except:
                print('Failed To Complete')
          

    def resetDesk(self):
        command = 'reset'
        command = command.encode()
        try:
            self.socket.send(command)
            msg = self.socket.recv()
        except:
            print('Error')

    def stopDesk(self):
            command = 'stop'
            command = command.encode()
            try:    
                self.socket.send(command)
                message = self.socket.recv()
            except:
                print('Failed To Complete')

if __name__ == '__main__':
    deskClient = deskclient(q=queue.Queue())
    deskClient.setDaemon(True)
    deskClient.start()
    while True:
        height_value = input("Enter in a height value: ")
        deskClient.onThread(deskClient.standDesk)