#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#

from fs100 import FS100
import os
import threading
import time
import traceback
import json
import random
import copy
import pathlib


class RobotController:
    def __init__(self, ip="192.168.250.101"):

        self.robot = FS100(ip)
        self.stop_sign = threading.Semaphore()
        self.monitorItems = []
        self.terminateMonitor = False
        self.monitorStatus = True
        self.isAlarmed = False
        self.isServoOn = False
        self.isRunning = False
        self.onHold = False

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

    def readItem(self, item):
        itemToRead = None
        if item["itemNum"] == "":
            return
        if item["itemType"] == "Integer":
            itemToRead = FS100.Variable(
                FS100.VarType.INTEGER, int(item["itemNum"]))
        if item["itemType"] == "Byte":
            itemToRead = FS100.Variable(
                FS100.VarType.BYTE, int(item["itemNum"]))
        if item["itemType"] == "IO":
            fullbyteaddress = item["itemNum"].split('.')
            bitaddress = -1
            byteaddress = 0
            if len(fullbyteaddress) > 1:
                bitaddress = int(fullbyteaddress[1])

            byteaddress = int(fullbyteaddress[0])
            itemToRead = FS100.Variable(
                FS100.VarType.IO, byteaddress)

        if itemToRead:

            if FS100.ERROR_SUCCESS == self.robot.read_variable(itemToRead):
                if item["itemType"] == "String":
                    val_str = itemToRead.val.rstrip("\x00")
                elif item["itemType"] == "RobotPosition":
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
                    if item["itemType"] == "IO" and bitaddress > -1:
                        n1 = f"{itemToRead.val:#010b}".replace(
                            '0b', '')[::-1]  # bin(itemToRead.val)[2:]
                        if bitaddress > 7:
                            bitaddress = 7
                        val_str = n1[bitaddress]
                    else:
                        val_str = str(itemToRead.val)

                # check if changed notify
                if val_str:

                    if ("itemValue" in item) == False:
                        item["itemValue"] = ""

                    currentValue = item["itemValue"]
                    if (val_str != currentValue) or item["notifyOnChange"] == False:
                        message = {
                            "command": "readitem",
                            "status": "valuereaded",
                            "id": item["id"],
                            "message": val_str,
                        }
                        messageJson = json.dumps(message)
                        self.sendToClient(messageJson)

                    item["itemValue"] = val_str
            else:

                message = "Failed to read the variable. ({})".format(
                    hex(self.robot.errno)
                )

                errorMessage = {
                    "command": "readitem",
                    "status": "readerror",
                    "id": item["id"],
                    "message": message,
                }
                errorMessageJson = json.dumps(errorMessage)
                self.sendToClient(errorMessageJson)
                print(message)

    def monitorWorker(self):
        """thread worker function"""
        print("Monitor vars thread started")
        while self.terminateMonitor == False:

            try:

                for monitorItem in self.monitorItems:

                    self.readItem(monitorItem)

                if self.monitorStatus:
                    self.readStatus()
                    self.readJobInfo()
                    # self.getAlarmStatus()

                time.sleep(0.1)

            except Exception as e:
                print(e.__class__, ":", e)
                print(traceback.format_exc())

            time.sleep(0.1)
        print("Monitor thread exit")

    def addMonitorItems(self, newMonitorItems):
        print("Reset monitor words")
        self.monitorItems = []
        for monitorItem in newMonitorItems:
            self.addMonitorItem(monitorItem)

    def addMonitorItem(self, newMonitorItem):
        itemfound = False
        for monitoritem in self.monitorItems:
            if monitoritem["id"] == newMonitorItem["id"]:
                itemfound = True
                break
        if itemfound == False:
            del newMonitorItem["itemValue"]
            self.monitorItems.append(newMonitorItem)
            print("Adding monitor item:", repr(newMonitorItem))

    def removeMonitorItem(self, monitorVarToRemove):

        for monitorvar in self.monitorItems:
            if monitorvar["id"] == monitorVarToRemove["id"]:
                self.monitorItems.remove(monitorvar)

                print("Removed monitor item:", repr(monitorVarToRemove))
                break

    def updateMonitoritem(self, monitorVarToUpdate):

        # for monitorvar in self.monitorItems:
        length = len(self.monitorItems)
        for i in range(length):
            monitorvar = self.monitorItems[i]
            if monitorvar["id"] == monitorVarToUpdate["id"]:
                # self.monitorItems.remove(monitorvar)

                # del monitorVarToUpdate['itemValue']

                print("Updated monitor item:", repr(monitorVarToUpdate))

                self.monitorItems[i] = copy.copy(monitorVarToUpdate)

                break

    def writeVariable(self, writeVar):
        varToWrite = None
        if writeVar["itemType"] == "Integer":
            varToWrite = FS100.Variable(
                FS100.VarType.INTEGER,
                int(writeVar["itemNum"]),
                int(writeVar["itemValue"]),
            )
        if writeVar["itemType"] == "Register":
            varToWrite = FS100.Variable(
                FS100.VarType.REGISTER,
                int(writeVar["itemNum"]),
                int(writeVar["itemValue"]),
            )
        if writeVar["itemType"] == "Byte":
            if writeVar["itemValue"]=='true':
                writeVar["itemValue"]=1
            if writeVar["itemValue"]=='false':
                writeVar["itemValue"]=0
                
            varToWrite = FS100.Variable(
                FS100.VarType.BYTE,
                int(writeVar["itemNum"]),
                int(writeVar["itemValue"]),
            )
        if writeVar["itemType"] == "IO":
            if writeVar["itemValue"]=='true':
                writeVar["itemValue"]=1
            if writeVar["itemValue"]=='false':
                writeVar["itemValue"]=0
                
            varToWrite = FS100.Variable(
                FS100.VarType.IO,
                int(writeVar["itemNum"]),
                int(writeVar["itemValue"]),
            )


        if varToWrite:

            if FS100.ERROR_SUCCESS == self.robot.write_variable(varToWrite):

                okMessage = {
                    "command": "writeitem",
                    "status": "OK",
                    "id": writeVar["id"],
                    "message": writeVar["itemValue"],
                }

                okMessageJson = json.dumps(okMessage)

                self.sendToClient(okMessageJson)
            else:
                message = "Failed to write the variable. ({})".format(
                    hex(self.robot.errno)
                )

                errorMessage = {
                    "command": "writeitem",
                    "status": "NOK",
                    "id": writeVar["id"],
                    "message": message,
                }
                errorMessageJson = json.dumps(errorMessage)
                self.sendToClient(errorMessageJson)
                print(message)

    def sendToClient(self, message):
        if hasattr(self, "tcpCLient") == False:
            return
        if self.tcpCLient._closed == False:
            message = message+'\r'
            self.tcpCLient.send(message.encode())

    def readStatus(self):
        status = {}
        if FS100.ERROR_SUCCESS == self.robot.get_status(status):

            onOld = status["hold_by_pendant"] or status["hold_externally"] or status["hold_by_cmd"] or status["teach"]
            if onOld:
                self.onHold = True

            status["on_hold"] = self.onHold

            statusMessage = {"command": "readstatus",
                             "status": "OK", "message": status}
            statusMessageJson = json.dumps(statusMessage)
            self.isAlarmed = status["alarming"]
            self.isServoOn = status["servo_on"]
            self.isRunning = status["running"]

            self.sendToClient(statusMessageJson)
            # print(status)

        else:
            message = "Failed to read status. ({})".format(
                hex(self.robot.errno))

            errorMessage = {
                "command": "readstatus",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            print(message)

    def readJobInfo(self):
        info = {}
        if FS100.ERROR_SUCCESS == self.robot.read_executing_job_info(info):

            statusMessage = {"command": "jobinfo",
                             "status": "OK", "message": info}
            statusMessageJson = json.dumps(statusMessage)
            # print(statusMessageJson)

            self.sendToClient(statusMessageJson)

        else:
            message = "Failed to read job info. ({})".format(
                hex(self.robot.errno))

            errorMessage = {
                "command": "jobinfo",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            # print(message)

    def getJobs(self):
        jobs = []
        message = {}
        if FS100.ERROR_SUCCESS != self.robot.get_file_list('*.JBI', jobs):

            message = "Failed to get jobs list. ({})".format(
                hex(self.robot.errno))

            errorMessage = {
                "command": "getjobs",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            print(message)
        else:
            message = {"command": "getjobs", "status": "OK", "message": jobs}
            messageJson = json.dumps(message)
            self.sendToClient(messageJson)

    def selectCycle(self, cycletype):

        message = {}

        if(cycletype == "CYCLE_TYPE_STEP"):
            fs100cycletype = FS100.CYCLE_TYPE_STEP
        elif(cycletype == "CYCLE_TYPE_ONE_CYCLE"):
            fs100cycletype = FS100.CYCLE_TYPE_ONE_CYCLE
        else:
            fs100cycletype = FS100.CYCLE_TYPE_CONTINUOUS
            self.onHold = False

        if FS100.ERROR_SUCCESS != self.robot.select_cycle(fs100cycletype):
            message = "failed select cycle type, err={}".format(
                hex(self.robot.errno))

            errorMessage = {
                "command": "selectcycle",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            print(message)

        else:
            message = {"command": "selectcycle",
                       "status": "OK", "message": ""}
            messageJson = json.dumps(message)
            self.sendToClient(messageJson)

    def getAlarmStatus(self):
        alarm = {}
        if FS100.ERROR_SUCCESS == self.robot.get_last_alarm(alarm):
            print("the last alarm: code={}, data={}, type={}, time={}, name={}"
                  .format(hex(alarm['code']), alarm['data'], alarm['type'], alarm['time'], alarm['name']))

    def softHold(self):

        message = {}

        self.robot.switch_power(FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_ON)
        # a hold off in case we switch to teach/play mode
        if FS100.ERROR_SUCCESS != self.robot.switch_power(FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_OFF):
            print("failed put on hold, err={}".format(
                hex(self.robot.errno)))
            time.sleep(2)
        else:

            message = {"command": "softhold",
                       "status": "OK", "message": "started"}
            messageJson = json.dumps(message)
            self.onHold = False
            self.sendToClient(messageJson)

    def playSelected(self):

        message = {}

        self.robot.switch_power(FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_ON)
        self.robot.switch_power(FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_OFF)

        if FS100.ERROR_SUCCESS != self.robot.switch_power(FS100.POWER_TYPE_SERVO, FS100.POWER_SWITCH_ON):
            print("failed turning on servo power supply, err={}".format(
                hex(self.robot.errno)))
            time.sleep(2)
        elif FS100.ERROR_SUCCESS != self.robot.play_job():

            message = "Failed to play job. ({})".format(
                hex(self.robot.errno))

            errorMessage = {
                "command": "playselected",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            print(message)
        else:

            message = {"command": "playselected",
                       "status": "OK", "message": "started"}
            messageJson = json.dumps(message)
            self.onHold = False
            self.sendToClient(messageJson)

    def startJob(self, jobname):

        message = {}
        status = {}
        p = pathlib.Path(jobname)
        jobname = p.with_name(p.name.split('.')[0]).with_suffix('.JBI').stem

        if FS100.ERROR_SUCCESS == self.robot.get_status(status):
            self.isRunning = status["running"]
        else:
            return

        if jobname.find('_RSTART') < 0:
            message = "Failed to start job.(Invalid remote start job selected)"

            errorMessage = {
                "command": "startjob",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            print(message)

            return

        if self.isRunning:
            message = "Failed to start job.(Job running)"

            errorMessage = {
                "command": "startjob",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            print(message)

            return

        if FS100.ERROR_SUCCESS != self.robot.select_job(jobname):

            message = "Failed to select job. ({})".format(
                hex(self.robot.errno))

            errorMessage = {
                "command": "startjob",
                "status": "NOK",
                "message": message,
            }
            errorMessageJson = json.dumps(errorMessage)
            self.sendToClient(errorMessageJson)
            print(message)
        else:
            if FS100.ERROR_SUCCESS != self.robot.switch_power(FS100.POWER_TYPE_SERVO, FS100.POWER_SWITCH_ON):
                print("failed turning on servo power supply, err={}".format(
                    hex(self.robot.errno)))
                time.sleep(2)
            else:
                if self.onHold:
                    self.robot.switch_power(
                        FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_ON)
                    # a hold off in case we switch to teach/play mode
                    self.robot.switch_power(
                        FS100.POWER_TYPE_HOLD, FS100.POWER_SWITCH_OFF)

                if FS100.ERROR_SUCCESS != self.robot.play_job():

                    message = "Failed to play job. ({})".format(
                        hex(self.robot.errno))

                    errorMessage = {
                        "command": "startjob",
                        "status": "NOK",
                        "message": message,
                    }
                    errorMessageJson = json.dumps(errorMessage)
                    self.sendToClient(errorMessageJson)
                    print(message)
                else:

                    message = {"command": "startjob",
                               "status": "OK", "message": "started"}
                    messageJson = json.dumps(message)
                    self.onHold = False
                    self.sendToClient(messageJson)

    def on_reset_alarm(self):
        self.robot.reset_alarm(FS100.RESET_ALARM_TYPE_ALARM)
        time.sleep(0.1)
        # reflect the ui
        self.is_alarmed()

    def get_position(self, event):
        pos_info = {}
        robot_no = 1
        if FS100.ERROR_SUCCESS == self.robot.read_position(pos_info, robot_no):
            x, y, z, rx, ry, rz, re = pos_info["pos"]
            str = (
                "CURRENT POSITION\n"
                + "COORDINATE {:12s} TOOL:{:02d}\n".format("ROBOT", pos_info["tool_no"])
                + "R{} :X     {:4d}.{:03d} mm       Rx   {:4d}.{:04d} deg.\n".format(
                    robot_no, x // 1000, x % 1000, rx // 10000, rx % 10000
                )
                + "    Y     {:4d}.{:03d} mm       Ry   {:4d}.{:04d} deg.\n".format(
                    y // 1000, y % 1000, ry // 10000, ry % 10000
                )
                + "    Z     {:4d}.{:03d} mm       Rz   {:4d}.{:04d} deg.\n".format(
                    z // 1000, z % 1000, rz // 10000, rz % 10000
                )
                + "                            Re   {:4d}.{:04d} deg.\n".format(
                    re // 10000, re % 10000
                )
            )

    # def is_alarmed(self):
    #     alarmed = False
    #     status = {}
    #     if FS100.ERROR_SUCCESS == self.robot.get_status(status):
    #         alarmed = status["alarming"]
    #     # if alarmed:
    #     #     self.reset_alarm.configure(state='normal')
    #     # else:
    #     #     self.reset_alarm.configure(state='disabled')
    #     return alarmed

    def start_move(self, event):
        MAX_XYZ = 90000
        MAX_R_XYZE = 180000
        SPEED_XYZ = (10, 100, 500)
        SPEED_R_XYZE = (10, 50, 100)
        x, y, z, rx, ry, rz, re = 0, 0, 0, 0, 0, 0, 0

        axis = event.widget.cget("text")
        if axis == "X+":
            x = MAX_XYZ
        elif axis == "X-":
            x = -MAX_XYZ
        elif axis == "Y+":
            y = MAX_XYZ
        elif axis == "Y-":
            y = -MAX_XYZ
        elif axis == "Z+":
            z = MAX_XYZ
        elif axis == "Z-":
            z = -MAX_XYZ
        elif axis == "Rx+":
            rx = MAX_R_XYZE
        elif axis == "Rx-":
            rx = -MAX_R_XYZE
        elif axis == "Ry+":
            ry = MAX_R_XYZE
        elif axis == "Ry-":
            ry = -MAX_R_XYZE
        elif axis == "Rz+":
            rz = MAX_R_XYZE
        elif axis == "Rz-":
            rz = -MAX_R_XYZE
        elif axis == "E+":
            re = MAX_R_XYZE
        elif axis == "E-":
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
            if not status["servo_on"]:
                self.robot.switch_power(
                    FS100.POWER_TYPE_SERVO, FS100.POWER_SWITCH_ON)

        self.pos_updater = threading.Thread(target=self.update_pos)
        if FS100.ERROR_SUCCESS == self.robot.one_move(
            FS100.MOVE_TYPE_LINEAR_INCREMENTAL_POS,
            FS100.MOVE_COORDINATE_SYSTEM_ROBOT,
            speed_class,
            speed,
            pos,
        ):
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
