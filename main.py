#!/usr/bin/env python
#
#
# Copyright (C) 2019, 2021 DFit
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# Authors:
#    Rui Sebastião <rui.sebastiao@dreamforit.com>
#


import socketserver
import threading
import json
import traceback
from robotController import RobotController
import signal
import sys
from functools import partial


class connectionHandler(socketserver.BaseRequestHandler):

    def processDataReceived(self, data):
        #info = '{"name": "Dave","City": "NY"}'

        try:

            datasplited=data.decode().split('\n');

            for commanddata in datasplited:
                if len(commanddata)==0: continue
                res = json.loads(commanddata)
                if(res['command']):
                    command = res['command']
                    if command == 'AddMonitorVar':
                        monitorvar = res['value']
                        self.server.robotcontroller.addMonitorVar(monitorvar)
                    if command == 'RemoveMonitorVar':
                        monitorvar = res['value']
                        self.server.robotcontroller.removeMonitorVar(monitorvar)
            # print(res['command'])
        except Exception as e:
            print(e.__class__, ':', e)
            print(traceback.format_exc())

    def handle(self):
        print('Client connected')
        self.server.robotcontroller.tcpCLient = self.request
        while 1:
            dataReceived = self.request.recv(1024)
            if not dataReceived:
                break
            print("Data received:", dataReceived)
            self.processDataReceived(dataReceived)
            # self.request.send(dataReceived)

def exit_gracefully(signum, robotcontroller):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant
    
    print("Ok ok, quitting")
    robotcontroller.terminateMonitorVars=True
    sys.exit(0)

   
    
if __name__ == '__main__':
    # store the original SIGINT handler
   
    robotcontroller = RobotController('192.168.250.101')
    # signal.signal(signal.SIGINT, partial(exit_gracefully, robotcontroller))
    
    
    socketserver.TCPServer.allow_reuse_address = 1
    tcpserver = socketserver.TCPServer(('0.0.0.0', 8881), connectionHandler)
    tcpserver.robotcontroller = robotcontroller
        
    tcpserver.serve_forever()
       