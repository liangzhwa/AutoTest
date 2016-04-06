# -*- coding: utf-8 -*-

"""
Module implementing MainWindow.
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from lib.Ui_AutoBisect import Ui_MainWindow
from lib import RunDaily, RunBisect, ProcManager
import PyQt4, os, sys, subprocess
import json
import time
import threading

QTextCodec.setCodecForTr(QTextCodec.codecForName("utf8"))

class MainWindow(QMainWindow, Ui_MainWindow):
    conf = {}
    testType = "autorun"
    buildType = "M"
    caseType = ""
    deviceType = ""
    runProc = None
    """
    Class documentation goes here.
    """
    def __init__(self, parent=None):
        """
        Constructor
        
        @param parent reference to the parent widget (QWidget)
        """

        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.btnStart.setStyleSheet("QPushButton {background-color:lightgray; color: black;}")
        self.btnDownload.setStyleSheet("QPushButton {background-color:lightgray; color: black;}")
        self.curPath = os.path.split(os.path.abspath(__file__))[0]
        if self.curPath.endswith("lib"):
            os.chdir(self.curPath)
        else:
            os.chdir(self.curPath+"/lib")
        self.conf = json.load(file("../conf/args.json"))

        osHardware = os.popen("adb shell getprop ro.product.board").read()
        if osHardware == "SF_3GR":
            self.rb3gr.checked = True
        elif osHardware == "SF_LTE":
            self.checked = True
            
        taskList = map(lambda x:x.strip(),open("../conf/tasklist.config", "r").readlines())
        self.listTask.addItems(taskList)
        
    @pyqtSignature("")
    def on_btnShowTask_clicked(self):
        tasklistfile = self.curPath.replace("\\lib","") + "/conf/tasklist.config"
        os.popen("notepad " + tasklistfile)
        taskList = map(lambda x:x.strip(),open(tasklistfile, "r").readlines())
        self.listTask.clear()
        self.listTask.addItems(taskList)
    @pyqtSignature("")
    def on_btnShowHistory_clicked(self):
        historyfile = self.curPath.replace("\\lib","") + "/log/history.log"
        os.popen("notepad "+historyfile)
    @pyqtSignature("")
    def on_btnShowLog_clicked(self):
        autorunfile = self.curPath.replace("\\lib","") + "/log/autorun.log"
        os.popen("notepad "+autorunfile)
    @pyqtSignature("")
    def on_btnShowRuned_clicked(self):
        if len(self.deviceType)==0:
            QMessageBox.information(self,"Notice", self.tr("请选择板子类型！"))
            return
        filename = self.curPath.replace("\\lib","") + "/conf/"+self.conf ["versionLog"][self.buildType]
        os.popen("notepad "+filename)
    
    @pyqtSignature("")
    def on_rbMBuild_clicked(self):
        self.buildType = "M"
    @pyqtSignature("")
    def on_rbLBuild_clicked(self):
        self.buildType = "L"

    @pyqtSignature("")
    def on_rb3gr_clicked(self):
        self.deviceType = "3gr"
        self.rbLBuild.setEnabled(True)
        self.rbLBuild.setChecked(True)
        if time.localtime().tm_wday == 1:
            self.rbMBuild.setChecked(True)
            self.buildType = "M"
        else:
            self.rbLBuild.setChecked(True)
            self.buildType = "L"
        self.updateArg()        
    @pyqtSignature("")
    def on_rblte_clicked(self):
        self.deviceType = "lte"
        self.rbLBuild.setEnabled(False)
        self.rbMBuild.setChecked(True)
        self.buildType = "M"
        self.updateArg()
        
    @pyqtSignature("")
    def on_rbPerf_clicked(self):
        self.caseType = "perf"
        self.updateArg()

        self.listCases.clear()
        listPerfCases = map(lambda x:x.strip(),open("../conf/perf.config", "r").readlines())
        self.listCases.addItems(listPerfCases)
    @pyqtSignature("")
    def on_rbPower_clicked(self):
        self.caseType = "power"
        self.updateArg()

        self.listCases.clear()
        listPowerCases = map(lambda x:x.strip(),open("../conf/power.config", "r").readlines())
        self.listCases.addItems(listPowerCases)
    
    @pyqtSlot()
    def on_listCases_itemSelectionChanged(self):
        if self.testType == "bisect":
            self.txtCampaign.setText(self.conf["campaign"][self.testType][self.caseType][self.deviceType].replace("$campaign$", self.listCases.currentItem().text().split(":")[1].trimmed()))

    @pyqtSignature("")
    def on_btnStart_clicked(self):
        global runProc
        #sendDataThread=threading.Thread(target=self.StartRun)
        if self.btnStart.text() == "Start Run":
            comCode = self.txtComcode.text()
            arg_campaign = self.txtCampaign.text()
            arg_device = self.txtDevice.text()
            arg_benchcfg = self.txtBenchcfg.text()
            arg_cr = self.conf["arg_cr"]
            if len(self.caseType)==0 or len(self.deviceType)==0 or len(comCode)==0 or  len(arg_campaign)==0 or  len(arg_device)==0 or  len(arg_benchcfg)==0 or  len(arg_cr)==0:
                QMessageBox.information(self,"Notice", self.tr("Please complete the args!!"))
                self.btnStart.setEnabled(True)
                return
            curPath = os.path.split(os.path.abspath(__file__))[0]
            if not self.curPath.endswith("lib"):
                curPath += "/lib"
            runProc = subprocess.Popen("python "+curPath+"/RunTask.py %s %s %s %s %s %s %s %s" % (self.caseType, self.deviceType, self.buildType,comCode,arg_campaign, arg_device, arg_benchcfg, arg_cr), shell=False)        
            #sendDataThread.start()
            self.btnStart.setStyleSheet("QPushButton {background-color:red; color: white;}")
            self.btnStart.setText("Stop Run")
        else:
            ProcManager.killPid(runProc.pid)
            #runProc.kill()
            self.btnStart.setStyleSheet("QPushButton {background-color:lightgray; color: black;}")
            self.btnStart.setText("Start Run")
            
    @pyqtSignature("")
    def on_btnDownload_clicked(self):
        if self.btnDownload.text() == "Start Download":
            if  len(self.deviceType)==0:
                QMessageBox.information(self,"Notice", self.tr("Please select the device type！"))
                return
            
            curPath = os.path.split(os.path.abspath(__file__))[0]
            if not self.curPath.endswith("lib"):
                curPath += "/lib"

            #subprocess.Popen("start python "+curPath+"/MergeRequest.py %s %s" % (self.deviceType, self.buildType), shell=True)
            subprocess.Popen("start python "+curPath+"/Download.py %s %s" % (self.deviceType, self.buildType), shell=True)
            self.btnDownload.setStyleSheet("QPushButton {background-color:red; color: white;}")
            self.btnDownload.setText("Stop Download")
        else:
            os.system('TASKKILL /F /IM python.exe /FI "WINDOWTITLE eq Administrator: *" /FI "WINDOWTITLE ne Administrator: C*')
            self.btnDownload.setStyleSheet("QPushButton {background-color:lightgray; color:black;}")
            self.btnDownload.setText("Start Download")
            
    def StartRun(self):
        comCode = self.txtComcode.text()
        arg_campaign = self.txtCampaign.text()
        arg_device = self.txtDevice.text()
        arg_benchcfg = self.txtBenchcfg.text()
        arg_cr = self.conf["arg_cr"]
        if len(self.caseType)==0 or len(self.deviceType)==0 or len(comCode)==0 or  len(arg_campaign)==0 or  len(arg_device)==0 or  len(arg_benchcfg)==0 or  len(arg_cr)==0:
            QMessageBox.information(self,"Notice", self.tr("Please complete the args!!"))
            self.btnStart.setEnabled(True)
            return
        if self.testType == "bisect":
            index = self.listCases.currentRow()
            if index <= -1:
                QMessageBox.information(self,"Notice", self.tr("Please select the test case！"))
                return
                
            item = self.listCases.item(index)
            sBuild=self.startCode.text()
            eBuild=self.endCode.text()
            caseNo=item.text().split(":")[0].trimmed()
            sValue=self.startValue.text()
            eValue=self.endValue.text()    
            if sBuild.isEmpty() or eBuild.isEmpty() or sValue.isEmpty() or eValue.isEmpty():
                QMessageBox.information(self,"Notice", self.tr("please input the args！"))
                return
            RunBisect.Start(self.caseType, self.deviceType, comCode,arg_campaign, arg_device, arg_benchcfg, arg_cr, str(sBuild),str(eBuild), str(caseNo), float(str(sValue)), float(str(eValue)))
        elif self.testType == "autorun":
            while 1:
                tasklist = RunDaily.getTaskList()
                if len(tasklist) > 0:
                    imageTpl = self.conf["imageTpl"][self.deviceType][self.buildType]
                    for task in tasklist:
                        imageName = ""
                        if len(task.split(" ")) != 2:
                            continue

                        if task.startswith("IL") or task.startswith("LB") or task.startswith("MR") or task.startswith("WB"):
                            imageName = "../images/" + task.split(" ")[1]
                            if not os.path.exists(imageName):
                                print("image %s not exists!"%(imageName))
                                RunDaily.writelog("image %s not exists!"%(imageName))
                        else:
                            local = task.split(" ")[0]
                            ebcode = task.split(" ")[1].strip()
                            imageURL = imageTpl % (local,ebcode,ebcode.zfill(6))
                            imageName = "../images/" + imageURL.split("/")[-1]
                            if not os.path.exists(imageName):
                                RunDaily.downloadbyurl(imageURL,imageName)
                        self.listRunLog.addItem("[ACS Start] Task:" + task)
                        time.sleep(10)
                        result = RunDaily.runTask(task, imageName, self.caseType, self.deviceType, self.buildType,comCode,arg_campaign, arg_device, arg_benchcfg, arg_cr)
                        msg = "Success" if result else "Failed"
                        self.listRunLog.addItem("[ACS Run Finished] Task: %s Result: %s" % (task, msg))
                        if task.startswith("LB"):
                            RunDaily.UpdateReleaseInfo(task.split(" ")[1][-10:-4].lstrip("0"),self.buildType)
                print "Please wait 360S for next round to run..."
                for i in range(360):
                    if isRun:
                        self.PrintMessage("====== %s ======" % (str(i)))
                        time.sleep(1)
                    else:
                        break
            self.btnStart.setStyleSheet("QPushButton {background-color:lightgray; color:black;}")
            self.btnStart.setText("Start Run")
            
    def Updatelog(self, msg):
        self.listRunLog.addItem(time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg + "\n")

    def updateArg(self):
        if self.deviceType != "" and self.caseType != "" :
            self.txtComcode.setText(self.conf["serialcode"][self.caseType][self.deviceType])
            self.txtDevice.setText(self.conf["device"][self.caseType][self.deviceType])
            self.txtBenchcfg.setText(self.conf["benchcfg"][self.caseType][self.deviceType])
        if  self.testType != "" and self.deviceType != "" and self.caseType != "":
            self.txtCampaign.setText(self.conf["campaign"][self.testType][self.caseType][self.deviceType])
    def PrintMessage(self,msg):
        print >>sys.stderr,'\r',
        print >>sys.stderr,msg,


if __name__=="__main__":
    app = PyQt4.QtGui.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
