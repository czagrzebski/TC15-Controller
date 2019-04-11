from flask import Flask
from flask_ask import Ask, request, session, question, statement
import zmq
import threading
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

import logging
import os





app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)

STATUSON = ['stand','standing']
STATUSOFF = ['sit','sitting']
RESET = ['reset', 'fix']

@ask.launch
def launch():
    speech_text = 'Welcome to SmartDesk Intent. Please say a command'
    return question(speech_text).reprompt(speech_text).simple_card(speech_text)

@ask.intent('GpioIntent', mapping = {'status':'status'})
def Desk_Intent(status,room):
    if status in STATUSON:
       deskClient.onThread(deskClient.standDesk)
       return statement('Setting smartdesk to {} mode'.format(status))
    elif status in STATUSOFF:
        deskClient.onThread(deskClient.sitDesk)
        return statement('Setting smartdesk to {} mode'.format(status))
    elif status in RESET:
        deskClient.onThread(deskClient.resetDesk)
        return statement('Resetting Smart Desk')
    else:
        return statement('Sorry I did not understand')
 
@ask.intent('AMAZON.HelpIntent')
def help():
    speech_text = 'Need help?'
    return question(speech_text).reprompt(speech_text).simple_card('HelloWorld', speech_text)


@ask.session_ended
def session_ended():
    return "{}", 200


if __name__ == '__main__':
    deskClient = deskclient(q=queue.Queue())
    deskClient.setDaemon(True)
    deskClient.start()
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
        if verify == 'false':
            app.config['ASK_VERIFY_REQUESTS'] = False
    port = 5000
    app.run(debug=True, port=port)





 
