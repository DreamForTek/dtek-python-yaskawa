#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#

from fs100 import FS100
import os
import threading
import time
import traceback
import json


class RobotController:
    def __init__(self, ip='192.168.250.101'):

        self.robot = FS100(ip)
        self.stop_sign = threading.Semaphore()
        self.monitorItems = []
        self.terminateMonitor = False
        self.thread = threading.Thread(target=self.monitorWorker, args=())
        self.thread.start()
        # set 'reset alarm' button state
        # self.is_alarmed()

    def __exit__(self):
        # body of destructor
        print("Terminating monitor thread")
        self.terminateMonitor = True
        self.thread.join()
        print("Monitor thread terminated")

    def __enter__(self):
        pass

    def clearVars(self):
        self.monitorItems.clear()

    def read_Item(self, item):
        if item['monitorType'] == "Variable":

            varToRead = None

            if item['varType'] == "Integer":
                varToRead = FS100.Variable(
                    FS100.VarType.INTEGER, int(item['varNum']))

            if varToRead:

                if FS100.ERROR_SUCCESS == self.robot.read_variable(varToRead):
                    if item['varType'] == "String":
                        val_str = varToRead.val.rstrip('\x00')
                    elif item['varType'] == "RobotPosition":
                        # val_str = "Data type: [{}]\n".format(str(var.val['data_type']))
                        # val_str += "Form: [{}]\n".format(str(var.val['form']))
                        # val_str += "Tool number: [{}]\n".format(str(var.val['tool_no']))
                        # val_str += "User coordinate number: [{}]\n".format(str(var.val['user_coor_no']))
                        # val_str += "Extended form: [{}]\n".format(str(var.val['extended_form']))
                        # val_str += "Coordinated data: [{}], [{}], [{}], [{}], [{}], [{}], [{}]".format(
                        #     str(var.val['pos'][0]),
                        #     str(var.val['pos'][1]),
                        #     str(var.val['pos'][2]),
                        #     str(var.val['pos'][3]),
                        #     str(var.val['pos'][4]),
                        #     str(var.val['pos'][5]),
                        #     str(var.val['pos'][6]))
                        pass
                    else:
                        val_str = str(varToRead.val)

                    # check if changed notify
                    if val_str:
                        item['varvalue'] = val_str
                else:

                    message = "Failed to read the variable. ({})".format(
                        hex(self.robot.errno))

                    errorMessage = {
                        'command': 'readError',
                        'varID': item['varID'],
                        'message': message
                    }
                    errorMessageJson = json.dumps(errorMessage)
                    if self.tcpCLient._closed == False:
                        self.tcpCLient.send(errorMessageJson.encode())
                    print(message)

    def monitorWorker(self):
        """thread worker function"""
        print('Monitor vars thread started')
        while self.terminateMonitor == False:

            try:

                for monitorItem in self.monitorItems:

                    self.read_Item(monitorItem)

            except Exception as e:
                print(e.__class__, ':', e)
                print(traceback.format_exc())

            time.sleep(0.1)
        print("Monitor thread exit")

    def addMonitorItem(self, newMonitorItem):
        itemfound = False
        for monitoritem in self.monitorItems:
            if monitoritem['varID'] == newMonitorItem['varID']:
                itemfound = True
                break
        if itemfound == False:
            self.monitorItems.append(newMonitorItem)
        # vartype=monitorVar['type']

    def removeMonitorItem(self, monitorVarToRemove):

        for monitorvar in self.monitorItems:
            if monitorvar['varID'] == monitorVarToRemove['varID']:
                self.monitorItems.remove(monitorvar)
                break

    def writeVariable(self, writeVar):
        varToWrite = None
        if writeVar['varType'] == "Integer":
            varToWrite = FS100.Variable(
                FS100.VarType.INTEGER, int(writeVar['varNum']), int(writeVar['varValue']))

            if varToWrite:

                if FS100.ERROR_SUCCESS == self.robot.write_variable(varToWrite):
                    pass
                else:
                    message = "Failed to write the variable. ({})".format(
                        hex(self.robot.errno))

                    errorMessage = {
                        'command': 'writeError',
                        'varID': writeVar['varID'],
                        'message': message
                    }
                    errorMessageJson = json.dumps(errorMessage)
                    if self.tcpCLient._closed == False:
                        self.tcpCLient.send(errorMessageJson.encode())
                    print(message)

    def readStatus(self):
        status = {}
        if FS100.ERROR_SUCCESS == self.robot.get_status(status):

            statusMessage = {
                'command': 'readStatus',
                'message': status
            }
            statusMessageJson = json.dumps(statusMessage)
            if self.tcpCLient._closed == False:
                self.tcpCLient.send(statusMessageJson.encode())

        else:
            message = "Failed to read status. ({})".format(
                hex(self.robot.errno))

            errorMessage = {
                'command': 'readStatusError',
                'message': message
            }
            errorMessageJson = json.dumps(errorMessage)
            if self.tcpCLient._closed == False:
                self.tcpCLient.send(errorMessageJson.encode())
            print(message)

    def on_reset_alarm(self):
        self.robot.reset_alarm(FS100.RESET_ALARM_TYPE_ALARM)
        time.sleep(0.1)
        # reflect the ui
        self.is_alarmed()

    def get_position(self, event):
        pos_info = {}
        robot_no = 1
        if FS100.ERROR_SUCCESS == self.robot.read_position(pos_info, robot_no):
            x, y, z, rx, ry, rz, re = pos_info['pos']
            str = "CURRENT POSITION\n" +\
                  "COORDINATE {:12s} TOOL:{:02d}\n".format('ROBOT', pos_info['tool_no']) +\
                  "R{} :X     {:4d}.{:03d} mm       Rx   {:4d}.{:04d} deg.\n".format(robot_no,
                                                                                     x // 1000, x % 1000, rx // 10000, rx % 10000) +\
                  "    Y     {:4d}.{:03d} mm       Ry   {:4d}.{:04d} deg.\n".format(
                      y // 1000, y % 1000, ry // 10000, ry % 10000) +\
                  "    Z     {:4d}.{:03d} mm       Rz   {:4d}.{:04d} deg.\n".format(
                      z // 1000, z % 1000, rz // 10000, rz % 10000) +\
                  "                            Re   {:4d}.{:04d} deg.\n".format(
                      re // 10000, re % 10000)

    def is_alarmed(self):
        alarmed = False
        status = {}
        if FS100.ERROR_SUCCESS == self.robot.get_status(status):
            alarmed = status['alarming']
        # if alarmed:
        #     self.reset_alarm.configure(state='normal')
        # else:
        #     self.reset_alarm.configure(state='disabled')
        return alarmed

    def start_move(self, event):
        MAX_XYZ = 90000
        MAX_R_XYZE = 180000
        SPEED_XYZ = (10, 100, 500)
        SPEED_R_XYZE = (10, 50, 100)
        x, y, z, rx, ry, rz, re = 0, 0, 0, 0, 0, 0, 0

        axis = event.widget.cget("text")
        if axis == 'X+':
            x = MAX_XYZ
        elif axis == 'X-':
            x = -MAX_XYZ
        elif axis == 'Y+':
            y = MAX_XYZ
        elif axis == 'Y-':
            y = -MAX_XYZ
        elif axis == 'Z+':
            z = MAX_XYZ
        elif axis == 'Z-':
            z = -MAX_XYZ
        elif axis == 'Rx+':
            rx = MAX_R_XYZE
        elif axis == 'Rx-':
            rx = -MAX_R_XYZE
        elif axis == 'Ry+':
            ry = MAX_R_XYZE
        elif axis == 'Ry-':
            ry = -MAX_R_XYZE
        elif axis == 'Rz+':
            rz = MAX_R_XYZE
        elif axis == 'Rz-':
            rz = -MAX_R_XYZE
        elif axis == 'E+':
            re = MAX_R_XYZE
        elif axis == 'E-':
            re = -MAX_R_XYZE

        if x != 0 or y != 0 or z != 0:
            speed_class = FS100.MOVE_SPEED_CLASS_MILLIMETER
            speed = SPEED_XYZ[self.speed.get()]
        else:
            speed_class = FS100.MOVE_SPEED_CLASS_DEGREE
            speed = SPEED_R_XYZE[self.speed.get()]
        pos = (x, y, z, rx, ry, rz, re)

        status = {}
        if FS100.ERROR_SUCCESS == self.robot.get_status(status):
            if not status['servo_on']:
                self.robot.switch_power(
                    FS100.POWER_TYPE_SERVO, FS100.POWER_SWITCH_ON)

        self.pos_updater = threading.Thread(target=self.update_pos)
        if FS100.ERROR_SUCCESS == self.robot.one_move(FS100.MOVE_TYPE_LINEAR_INCREMENTAL_POS,
                                                      FS100.MOVE_COORDINATE_SYSTEM_ROBOT, speed_class, speed, pos):
            time.sleep(0.1)  # robot may not update the status
            if not self.is_alarmed():
                self.pos_updater.start()

    def stop_move(self, event):
        self.stop_sign.acquire()

        while self.pos_updater.is_alive():
            pass

        self.robot.switch_power(FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_ON)
        # a hold off in case we switch to teach/play mode
        self.robot.switch_power(FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_OFF)

        # the position of robot in still
        # self.position_text.event_generate("<<update>>")

        self.stop_sign.release()
