#!/usr/bin/env python
#
#
# Copyright (C) 2019, 2021 DFit
#
# Authors:
#    Rui Sebastião <rui.sebastiao@dreamforit.com>
#

# Ver: 1.0.6

import socketserver
import threading
import json
import traceback
from robotController import RobotController
import os
import sys
from functools import partial

import argparse

import psutil


# Instantiate the parser
parser = argparse.ArgumentParser(description='Dtek python Yaskawa')


parser.add_argument('-p', '--port', type=int,
                    help='tcp server port number')


parser.add_argument('-i', '--ip', type=str,
                    help='Robot ip number')


parser.add_argument('-m', '--multiple', action='store_true',
                    help='Allow multiple instances')

parser.add_argument('-d', '--id', type=str,
                    help='id')


args = parser.parse_args()


serverport = args.port if args.port else 8881

robotIp = args.ip if args.ip else '192.168.250.101'


def checkIfRunning():
    for p in psutil.process_iter():
        cmdline = p.cmdline()
        process_id = os.getpid()
        if 'python' in p.name():
            for cmd in cmdline:
                if (args.id and args.id in cmd) and (process_id != p.pid):
                    print("Terminating running dtek-python-yaskawa:", p)
                    p.kill()
                    break
    print("Check running done")


class connectionHandler(socketserver.BaseRequestHandler):

    def processDataReceived(self, data):
        # info = '{"name": "Dave","City": "NY"}'

        allcommandreceived = (data[len(data)-1]) == 13
        self.alldatareceived += data.decode()
        if self.alldatareceived.find('\r') == -1:
            return

        try:

            self.alldatareceived = self.alldatareceived.replace('\n', '')

            datasplited = self.alldatareceived.split('\r')

            for commanddata in datasplited:
               
                # commanddata = commanddata.replace('\r', '')

                if len(commanddata) <2 or  commanddata[len(commanddata)-1]!='\n':
                    continue
                res = json.loads(commanddata)
                if (res['command']):
                    command = res['command']
                    if command == 'addmonitoritem':
                        monitoritem = res['value']
                        self.server.robotcontroller.addMonitorItem(monitoritem)
                    if command == 'addmonitoritems':
                        monitoritems = res['values']
                        self.server.robotcontroller.addMonitorItems(
                            monitoritems)
                    if command == 'removemonitoritem':
                        monitoritem = res['value']
                        self.server.robotcontroller.removeMonitorItem(
                            monitoritem)
                    if command == 'writeitem':
                        monitoritem = res['value']
                        self.server.robotcontroller.writeVariable(monitoritem)
                    if command == 'updatemonitoritem':
                        monitoritem = res['value']
                        self.server.robotcontroller.updateMonitoritem(
                            monitoritem)
                    if command == 'readstatus':
                        # monitoritem = res['value']
                        self.server.robotcontroller.readStatus()
                    if command == 'getjobs':
                        # monitoritem = res['value']
                        self.server.robotcontroller.getJobs()
                    if command == 'startjob':
                        jobname = res['value']
                        self.server.robotcontroller.startJob(jobname)
                    if command == 'selectcycle':
                        cycletype = res['value']
                        self.server.robotcontroller.selectCycle(cycletype)
                    if command == 'playjob':
                        self.server.robotcontroller.playSelected()
                    if command == 'softhold':
                        self.server.robotcontroller.softHold()

            if allcommandreceived == False:
                self.alldatareceived = datasplited[len(datasplited)-1]
            else:
                self.alldatareceived = ""

            # print(res['command'])
        except Exception as e:
            print(e.__class__, ':', e)
            print(traceback.format_exc())

    def handle(self):
        print('Client connected')

        self.alldatareceived = ""

        self.server.robotcontroller.tcpCLient = self.request

        self.server.robotcontroller.clearVars()
        self.server.robotcontroller.firstRun = True

        try:
            while 1:
                dataReceived = self.request.recv(8192)
                if not dataReceived:
                    break
                print("Data received:", dataReceived)
                self.processDataReceived(dataReceived)
        except Exception as e:
            print(e.__class__, ':', e)
            print(traceback.format_exc())
        finally:
            pass

        print("Client disconnected")


def exit_gracefully(signum, robotcontroller):
    # restore the original signal handler as otherwise evil things will happen
    # in raw_input when CTRL+C is pressed, and our signal handler is not re-entrant

    print("Ok ok, quitting")
    robotcontroller.terminateMonitorVars = True
    sys.exit(0)


if __name__ == '__main__':
    # store the original SIGINT handler

    if not args.multiple:
        checkIfRunning()

    robotcontroller = RobotController(robotIp)
    # signal.signal(signal.SIGINT, partial(exit_gracefully, robotcontroller))

    socketserver.TCPServer.allow_reuse_address = 1
    tcpserver = socketserver.TCPServer(('0.0.0.0', 8881), connectionHandler)
    tcpserver.robotcontroller = robotcontroller

    tcpserver.serve_forever()
