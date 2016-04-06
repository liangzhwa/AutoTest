# -*- coding: utf8 -*-
import os
import sys
import subprocess
import time
import logging as dailylog
import serial
import urllib2
from urllib2 import HTTPError
import smtplib
import json
import socket
import RunCmdWithTimeout
import RunCmdWithLimittime
import ProcManager

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

curPath = os.path.split(os.path.realpath(__file__))[0]
acsPath = "C:/Users/buildbot/Intel/ACS/acs_fwk/src"
acsCmd_template = """C:/Python27/python.exe "C:/Users/buildbot/Intel/ACS/acs_fwk/src/ACS.py" -c "%s" -d %s -b "%s" %s """
os.chdir(curPath)

dailylog.basicConfig(level=dailylog.DEBUG,filename='../log/autorun.log', filemode='a')
conf = json.load(file("../conf/args.json"))
username = conf["username"]
password = conf["password"]
versionLog = conf["versionLog"]

def getTaskList():
    tasklist = map(lambda x:x.strip(),open("../conf/tasklist.config",'r').readlines())
    tasklist = filter(lambda x:x != "",tasklist)
    print("Get Task List: [%s]" % (",".join(tasklist)))
    writelog("Get Task List: [%s]" % (",".join(tasklist)))
    writehistory("Get Task List: [%s]" % (",".join(tasklist)))
    return tasklist
def UpdateTaskList(task):
    tasklist = map(lambda x:x.strip()+"\n",open("../conf/tasklist.config",'r').readlines())
    if tasklist[0] == (task+"\n") :
        open("../conf/tasklist.config",'w').writelines(tasklist[1:])

def ConnectUSB(comCode):
    print("Device not found, try to connect the USB...")
    writelog("Device not found, try to connect the USB...")
    ser = serial.Serial(str(comCode), 19200, timeout=5)
    ser.write("j")
    ser.close()
    time.sleep(3)
def RestartDevices(comCode,cutpowertime):
    print("Device not found, cut the device's power by press power-key for %s s..." % (str(cutpowertime)))
    writelog("Device not found, cut the device's power by press power-key for %s s..." % (str(cutpowertime)))
    ser = serial.Serial(str(comCode), 19200, timeout=5)
    ser.write("i")
    time.sleep(cutpowertime)
    ser.write("s")
    time.sleep(3)
    print("Press power-key for 5 s to restart the device..")
    writelog("Press power-key for 5 s to restart the device..")
    ser.write("i")
    time.sleep(5)
    ser.write("s")
    time.sleep(10)
    ser.write("i")
    time.sleep(5)
    ser.write("s")
    print "Please wait 180S for device restart..."
    for i in range(180):
        PrintMessage("====== %s ======" % (str(i)))
        time.sleep(1)
    try:
        RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
    except Exception,e:
        if e.message == "TIMEOUT":
            print "Restart Device failed."
    ser.close()
def RecoverDevice(comCode,cutpowertime,deviceType,buildType):
    print("<<<<<<<<<<<Device not found, Recover Device: ")
    writelog("<<<<<<<<<<<Device not found, Recover Device: ")
    if Recover_PFT_ERASE(comCode,cutpowertime,deviceType,buildType,3):
        return True
    if Recover_PFT(comCode,cutpowertime,deviceType,buildType,3):
        return True
        
    if Recover_DT(comCode,cutpowertime,deviceType,buildType,1,3):
        return True
    if Recover_DT(comCode,cutpowertime,deviceType,buildType,0,3):
        return True
    return False

def Recover_PFT_ERASE(comCode,cutpowertime,deviceType,buildType,retry_count):
    recover_result = False
    CmdBase = 'C:/\"Program Files (x86)\"/Intel/\"Phone Flash Tool\"/DownloadTool.exe --verbose 4 -c USB1 --erase-mode=1 '
    recoverImage = conf["recoverImage"][deviceType][buildType]
    imagePath = os.path.abspath(recoverImage.replace(".zip",""))
    unzipImage(recoverImage)
    tmpList = filter(lambda x:x.endswith(".fls"),os.listdir(imagePath))
    tmpList.insert(0," ")
    dtCmd = CmdBase + (" "+imagePath+"/").join(tmpList)
    
    print("<<<<<<<<<<<Recover Device Start: Method: Recover_PFT_ERASE; Image: " + recoverImage)
    writelog("<<<<<<<<<<<Recover Device Start: Method: Recover_PFT_ERASE; Image: " + recoverImage)
    
    for i in range(retry_count):
        subprocess.Popen("python CutPower.py %s %s" % (comCode,cutpowertime))
        if os.system(dtCmd) == 0:
            print "Please wait 120S for device first starting..."
            for i in range(120):
                PrintMessage("====== %s ======" % (str(i)))
                time.sleep(1)
            RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=480,retry_count=0)
            recover_result = True
            break
    print("<<<<<<<<<<<Recover Device End: Method: Recover_PFT; Image: %s; Result: %s" % (recoverImage,str(recover_result)))
    writelog("<<<<<<<<<<<Recover Device End: Method: Recover_PFT; Image: %s; Result: %s" % (recoverImage,str(recover_result)))
    return recover_result
def Recover_PFT(comCode,cutpowertime,deviceType,buildType,retry_count):
    recover_result = False
    recoverImage = conf["recoverImage"][deviceType][buildType]
    flashcmd = conf["flashcmd"][deviceType] + recoverImage
    
    print("<<<<<<<<<<<Recover Device Start: Method: Recover_PFT; Image: " + recoverImage)
    writelog("<<<<<<<<<<<Recover Device Start: Method: Recover_PFT; Image: " + recoverImage)
    
    for i in range(retry_count):
        subprocess.Popen("python CutPower.py %s %s" % (comCode,cutpowertime))
        if os.system(flashcmd) == 0:
            print "Please wait 120S for device first starting..."
            for i in range(120):
                PrintMessage("====== %s ======" % (str(i)))
                time.sleep(1)
            RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=480,retry_count=0)
            recover_result = True
            break
    
    print("<<<<<<<<<<<Recover Device End: Method: Recover_PFT; Image: %s; Result: %s" % (recoverImage,str(recover_result)))
    writelog("<<<<<<<<<<<Recover Device End: Method: Recover_PFT; Image: %s; Result: %s" % (recoverImage,str(recover_result)))
    return recover_result

def Recover_FT(comCode,cutpowertime,deviceType,buildType,erasemode,retry_count):
    import win32com.client
    import win32api
    import ConfigParser
    try:               
        config = ConfigParser.ConfigParser()
        config.readfp(open('C:/FlashTool/FlashTool_E2.ini'))
        recoverImage = conf["recoverImage"][deviceType][buildType]
        imagePath = os.path.abspath(recoverImage.replace(".zip",""))
        unzipImage(recoverImage)
        for i in range(retry_count):
            print("Start %s ; Method: flashImage_FT(erase-mode=%s) ; -- flash image: %s" %(str(i),erasemode,recoverImage))
            writelog("Start %s ; Method: flashImage_FT(erase-mode=%s) ; -- flash image: %s" %(str(i),erasemode,recoverImage))            
            
            tmpList = filter(lambda x:x.endswith(".fls"),os.listdir(imagePath))
            
            for opt in config.options("Files"):
                if opt.startswith("downloadlist"):
                    config.set("Files", opt, "")
            for index,tmp in enumerate(tmpList):
                ser = str(index) if index > 0 else ""
                config.set("Files", "DownloadList"+ser, "+|0|" + imagePath + "\\" + tmp)
            config.set("Flags", "EraseMode", erasemode)
            config.write(open('C:/FlashTool/FlashTool_E2.ini', "r+"))
            
            shell = win32com.client.Dispatch("WScript.Shell")
            cmd = "start C:/FlashTool/FlashTool_E2.exe FlashTool_E2.ini -f"
            pipe = subprocess.Popen(cmd,stdin=None,stdout=None,stderr=subprocess.STDOUT,shell=True)
            #shell.Run("C:/FlashTool/FlashTool_E2.exe FlashTool_E2.ini -f")
            win32api.Sleep(3000)
            shell.AppActivate("Download")
            win32api.Sleep(5000)
            shell.SendKeys("{ENTER}")
            win32api.Sleep(3000)
            subprocess.Popen("python CutPower.py %s %s" % (comCode,"12"))
            print "Please wait 600S for flash image..."
            for j in range(600):
                PrintMessage("====== %s ======" % (str(j)))
                time.sleep(1)
            RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=300,retry_count=0)
            
            #check the build version
            cur = os.popen("adb shell getprop ro.build.version.incremental").read().strip()
            if recoverImage.find(cur) > 0:
                print("Build version checked OK!")
                writelog("Build version checked OK!")
                ProcManager.killPid(pipe.pid)
                #os.system("taskkill /F /IM FlashTool_E2.exe")
            else:
                print("Build version checked Failed!")
                writelog("Build version checked Failed!")
                ProcManager.killPid(pipe.pid)
                #os.system("taskkill /F /IM FlashTool_E2.exe")
                continue
            #after flash, reboot device
            bootmode = os.popen("adb shell getprop ro.bootmode").read().strip()
            if bootmode == "normal" or bootmode == "unknown":
                os.system("adb reboot")
                time.sleep(180)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
            else:
                RestartDevices(comCode,10)
                os.system("adb reboot")
                time.sleep(180)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
                
            if checkADB(deviceType,buildType,comCode):
                print(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Success!" % (str(i),erasemode,recoverImage))
                writelog(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Success!" % (str(i),erasemode,recoverImage))
                return True
            else:
                print(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Failed!" % (str(i),erasemode,recoverImage))
                writelog(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Failed!" % (str(i),erasemode,recoverImage))
        return False
    except Exception, e:
        print("Method: flashImage_FT(erase-mode=%s) ;An unexpected error occurred when flash image: %s.   %s" % (recoverImage,erasemode,e.message))
        writelog("Method: flashImage_FT(erase-mode=%s) ;An unexpected error occurred when flash image: %s.   %s" % (recoverImage,erasemode,e.message))
        return False


def checkADB(deviceType,buildType,comCode):
    curBuild = ""
    result = False
    cutpowertime = int(conf["cutpowertime"])
    restarttimes = int(conf["restarttimes"])
    versionCmd = "adb shell getprop ro.build.version.incremental"
    curBuild = os.popen(versionCmd).readlines()[-1].strip() if os.popen(versionCmd).readlines() else ""
    print 111111111111111111
    print curBuild,len(curBuild)
    print 222222222222222222
    if len(curBuild) != 9:
        ConnectUSB(comCode)
        curBuild = os.popen(versionCmd).readlines()[-1].strip() if os.popen(versionCmd).readlines() else ""
        if len(curBuild) != 9:
            for i in range(restarttimes):
                RestartDevices(comCode,cutpowertime)
                curBuild = os.popen(versionCmd).readlines()[-1].strip() if os.popen(versionCmd).readlines() else ""
                print 333333333333333333
                print curBuild,len(curBuild)
                print 444444444444444444
                if len(curBuild) == 9:
                    result = True
                    break
    else:
        result = True
    if result:
        os.system("adb root")
    else:
        RecoverDevice(comCode,cutpowertime,deviceType,buildType)
    print("^^^^^^ Check ADB: Result = [%s]; Build = [%s]. ^^^^^^" % (result,curBuild))
    return result
    
def PrintMessage(msg):
    print >>sys.stderr,'\r',
    print >>sys.stderr,msg,

def downloadbyurl(image_url,imageName,CallBackFunction=PrintMessage):
    if os.path.exists(imageName):
        return
    print "downloading image..."
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()    
    password_mgr.add_password(None, image_url, username, password)
    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)
    urllib2.install_opener(opener)
    try:
        response = urllib2.urlopen(image_url)
        outf = open(imageName,'wb')
        size = 0
        CallBackFunction('Download %s to %s \r'%(image_url,imageName))
        while True:
            tmp = response.read(1024*1024)
            if len(tmp) == 0:
                break
            outf.write(tmp)
            size += len(tmp)
            CallBackFunction('Download %d'%(size))
        print "\n"
        return size
    except HTTPError, e:
        if e.code == 404:
            print "Please wait 360S for EB compile..."
            for i in range(360):
                PrintMessage("====== %s ======" % (str(i)))
                time.sleep(1)
            downloadbyurl(image_url,imageName,CallBackFunction=PrintMessage) 
            
def flashImage(deviceType,buildType,comCode, imageName):
    if checkNeedFlash(deviceType,buildType,comCode, imageName):
        print("Start -- flash image: %s" %(imageName))
        writelog("Start -- flash image: %s" %(imageName))
        if not os.path.exists(imageName):
            print("Flash image failed.  Image File : %s not exists." % (imageName))
            writelog("Flash image failed.  Image File : %s not exists." % (imageName))
            return False
        
        if flashImage_PFT_ERASE(deviceType,buildType,comCode, imageName):
            return True
        
        if flashImage_PFT(deviceType,buildType,comCode, imageName):
            return True
            
        if flashImage_FT(deviceType,buildType,comCode, imageName,"1"):
            return True
            
        if flashImage_FT(deviceType,buildType,comCode, imageName,"0"):
            return True
        
    else:
        return True

def checkNeedUnzip(imageName):
    if os.path.exists(imageName.replace(".zip","") + "/flash.json"):
        confFile = file(imageName.replace(".zip","") + "/flash.json")
        conf = json.load(confFile)
        confFile.close()
        print conf["build_info"]["ro.build.version.incremental"]
        if imageName.find(conf["build_info"]["ro.build.version.incremental"]) > 0:
            return False
    return True
def unzipImage(imageName):
    if checkNeedUnzip(imageName):
        import zipfile
        if not os.path.exists(imageName):
            print "Image File : %s not exists." % (imageName)
            return
        if not os.path.exists(imageName.replace(".zip","")):
            os.mkdir(imageName.replace(".zip",""))
        for flsFile in os.listdir(imageName.replace(".zip","")):
            if os.path.isfile(flsFile):
                try:
                    os.remove(flsFile)
                except:
                    pass
        zfile = zipfile.ZipFile(imageName)
        for filename in zfile.namelist():
            zfile.extract(filename,imageName.replace(".zip",""))

def flashImage_PFT_ERASE(deviceType,buildType,comCode, imageName):
    CmdBase = 'C:/\"Program Files (x86)\"/Intel/\"Phone Flash Tool\"/DownloadTool.exe --verbose 4 -c USB1 --erase-mode=1 '
    imagePath = os.path.abspath(imageName.replace(".zip",""))
    unzipImage(imageName)

    tmpList = filter(lambda x:x.endswith(".fls"),os.listdir(imagePath))
    tmpList.insert(0," ")
    dtCmd = CmdBase + (" "+imagePath+"/").join(tmpList)
    reflashtimes = int(conf["reflashtimes"])
    try:
        for i in range(reflashtimes):
            print("Start %s ; Method: flashImage_PFT_ERASE ; -- flash image: %s" %(str(i),  imageName))
            writelog("Start %s ; Method: flashImage_PFT_ERASE ; -- flash image: %s" %(str(i),  imageName))
            
            subprocess.Popen("python CutPower.py %s %s" % (comCode,"10"))
            if os.system(dtCmd) == 0:
                print("End %s == ; Method: flashImage_PFT_ERASE ; flash Image finished.  %s" % (str(i), imageName))
                writelog("End %s == ; Method: flashImage_PFT_ERASE ; flash Image finished.  %s" % (str(i), imageName))
                print "Please wait 120S for device first starting..."
                for j in range(120):
                    PrintMessage("====== %s ======" % (str(j)))
                    time.sleep(1)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=480,retry_count=0)
                
                #after flash, reboot device
                bootmode = os.popen("adb shell getprop ro.bootmode").read().strip()
                if bootmode == "normal" or bootmode == "unknown":
                    os.system("adb reboot")
                    time.sleep(180)
                    RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
                else:
                    RestartDevices(comCode,10)
                    os.system("adb reboot")
                    time.sleep(180)
                    RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
                    
                if checkADB(deviceType,buildType,comCode):
                    print(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Success!" % (str(i), imageName))
                    writelog(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Success!" % (str(i), imageName))
                    return True
                else:
                    print(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Failed!" % (str(i), imageName))
                    writelog(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Failed!" % (str(i), imageName))
                    return False
            print("End %s ; Method: flashImage_PFT_ERASE ; == flash image failed.  %s." % (str(i),   imageName))
            writelog("End %s ; Method: flashImage_PFT_ERASE ; == flash image failed.  %s" % (str(i),  imageName))
        return False
    except Exception, e:
        print("Method: flashImage_PFT_ERASE ;An unexpected error occurred when flash image: %s.   %s" % (imageName, e.message))
        writelog("Method: flashImage_PFT_ERASE ;An unexpected error occurred when flash image: %s.   %s" % (imageName, e.message))
        return False
def flashImage_PFT(deviceType,buildType,comCode, imageName):
    flashcmd = conf["flashcmd"][deviceType] + imageName
    reflashtimes = int(conf["reflashtimes"])
    try:
        for i in range(reflashtimes):
            print("Start %s ; Method: flashImage_PFT_ERASE ; -- flash image: %s" %(str(i),  imageName))
            writelog("Start %s ; Method: flashImage_PFT_ERASE ; -- flash image: %s" %(str(i),  imageName))
            if i > 0:
                subprocess.Popen("python CutPower.py %s %s" % (comCode,"10"))
            if os.system(flashcmd) == 0:
                print("End %s == ; Method: flashImage_PFT_ERASE ; flash Image finished.  %s" % (str(i), imageName))
                writelog("End %s == ; Method: flashImage_PFT_ERASE ; flash Image finished.  %s" % (str(i), imageName))
                print "Please wait 180S for device first starting..."
                for j in range(180):
                    PrintMessage("====== %s ======" % (str(j)))
                    time.sleep(1)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=480,retry_count=0)
                
                #after flash, reboot device
                bootmode = os.popen("adb shell getprop ro.bootmode").read().strip()
                if bootmode == "normal" or bootmode == "unknown":
                    os.system("adb reboot")
                    time.sleep(180)
                    RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
                else:
                    RestartDevices(comCode,10)
                    os.system("adb reboot")
                    time.sleep(180)
                    RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)

                if checkADB(deviceType,buildType,comCode):
                    print(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Success!" % (str(i), imageName))
                    writelog(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Success!" % (str(i), imageName))
                    return True
                else:
                    print(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Failed!" % (str(i), imageName))
                    writelog(">>>>>>>>>>(%s) ; Method: flashImage_PFT_ERASE ; Flash Image finished[%s]. ADB Check Failed!" % (str(i), imageName))
                    return False
            print("End %s ; Method: flashImage_PFT_ERASE ; == flash image failed.  %s." % (str(i),   imageName))
            writelog("End %s ; Method: flashImage_PFT_ERASE ; == flash image failed.  %s" % (str(i),  imageName))
        return False
    except Exception, e:
        print("Method: flashImage_PFT_ERASE ;An unexpected error occurred when flash image: %s.   %s" % (imageName, e.message))
        writelog("Method: flashImage_PFT_ERASE ;An unexpected error occurred when flash image: %s.   %s" % (imageName, e.message))
        return False
def flashImage_FT(deviceType,buildType,comCode, imageName,erasemode):
    import win32com.client
    import win32api
    import ConfigParser
    try:               
        reflashtimes = int(conf["reflashtimes"])
        config = ConfigParser.ConfigParser()
        config.readfp(open('C:/FlashTool/FlashTool_E2.ini'))
        imagePath = os.path.abspath(imageName.replace(".zip",""))
        unzipImage(imageName)
        for i in range(reflashtimes):
            print("Start %s ; Method: flashImage_FT(erase-mode=%s) ; -- flash image: %s" %(str(i),erasemode,imageName))
            writelog("Start %s ; Method: flashImage_FT(erase-mode=%s) ; -- flash image: %s" %(str(i),erasemode,imageName))            
            
            tmpList = filter(lambda x:x.endswith(".fls"),os.listdir(imagePath))
            
            for opt in config.options("Files"):
                if opt.startswith("downloadlist"):
                    config.set("Files", opt, "")
            for index,tmp in enumerate(tmpList):
                ser = str(index) if index > 0 else ""
                config.set("Files", "DownloadList"+ser, "+|0|" + imagePath + "\\" + tmp)
            config.set("Flags", "EraseMode", erasemode)
            config.write(open('C:/FlashTool/FlashTool_E2.ini', "r+"))
            
            shell = win32com.client.Dispatch("WScript.Shell")
            cmd = "start C:/FlashTool/FlashTool_E2.exe FlashTool_E2.ini -f"
            pipe = subprocess.Popen(cmd,stdin=None,stdout=None,stderr=subprocess.STDOUT,shell=True)
            print pipe.pid
            #shell.Run("C:/FlashTool/FlashTool_E2.exe FlashTool_E2.ini -f")
            win32api.Sleep(3000)
            shell.AppActivate("Download")
            win32api.Sleep(5000)
            shell.SendKeys("{ENTER}")
            win32api.Sleep(3000)
            subprocess.Popen("python CutPower.py %s %s" % (comCode,"10"))
            print "Please wait 600S for flash image..."
            for j in range(600):
                PrintMessage("====== %s ======" % (str(j)))
                time.sleep(1)
            RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=300,retry_count=0)
            
            #check the build version
            cur = os.popen("adb shell getprop ro.build.version.incremental").read().strip()
            if imageName.find(cur) > 0:
                print("Build version checked OK!")
                writelog("Build version checked OK!")
                ProcManager.killPid(pipe.pid)
                #os.system("taskkill /F /IM FlashTool_E2.exe")
            else:
                print("Build version checked Failed!")
                writelog("Build version checked Failed!")
                ProcManager.killPid(pipe.pid)
                #os.system("taskkill /F /IM FlashTool_E2.exe")
            #after flash, reboot device
            bootmode = os.popen("adb shell getprop ro.bootmode").read().strip()
            if bootmode == "normal" or bootmode == "unknown":
                os.system("adb reboot")
                time.sleep(180)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
            else:
                RestartDevices(comCode,10)
                os.system("adb reboot")
                time.sleep(180)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=420,retry_count=0)
                
            if checkADB(deviceType,buildType,comCode):
                print(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Success!" % (str(i),erasemode,imageName))
                writelog(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Success!" % (str(i),erasemode,imageName))
                return True
            else:
                print(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Failed!" % (str(i),erasemode,imageName))
                writelog(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Failed!" % (str(i),erasemode,imageName))
        return False
    except Exception, e:
        print("Method: flashImage_FT(erase-mode=%s) ;An unexpected error occurred when flash image: %s.   %s" % (imageName,erasemode,e.message))
        writelog("Method: flashImage_FT(erase-mode=%s) ;An unexpected error occurred when flash image: %s.   %s" % (imageName,erasemode,e.message))
        return False

def runACS(arg_campaign, arg_device, arg_benchcfg, arg_cr, imageName,  index):
    try:
        rerunacstimes = int(conf["rerunacstimes"])
        print("Start %s == Run ACS: %s" % (str(index), imageName))
        writelog("Start %s == Run ACS: %s" % (str(index), imageName))
        writehistory("Start %s == Run ACS: %s" % (str(index), imageName))
        acsCmd = acsCmd_template % (arg_campaign,arg_device,arg_benchcfg,arg_cr)
        print("    ACS Cmd: " + acsCmd)
        writelog("    ACS Cmd: " + acsCmd)
        writehistory("    ACS Cmd: " + acsCmd)
        os.chdir(acsPath)
        #RunCmdWithTimeout.RunCommand(acsCmd,timeout_time=60,retry_count=0)
        RunCmdWithLimittime.RunCommand(acsCmd,limit_time=10800,retry_count=0)
        #acsResult = os.system(acsCmd)
        os.chdir(curPath)
        if acsResult == 0:
            print("End %s == Run ACS Success!: %s" % (str(index), imageName))
            writelog("End %s == Run ACS Success!: %s" % (str(index), imageName))
            writehistory("End %s == Run ACS Success!: %s" % (str(index), imageName))
            return True
        else:
            print("End %s == Run ACS Failed!(%s): %s" % (str(index), str(acsResult), imageName))
            writelog("End %s == Run ACS Failed!(%s): %s" % (str(index), str(acsResult), imageName))
            writehistory("End %s == Run ACS Failed!(%s): %s" % (str(index), str(acsResult), imageName))
            if index < rerunacstimes:
                index += 1
                runACS(arg_campaign, arg_device, arg_benchcfg, arg_cr, imageName,  index)
            else:
                return False
    except Exception,e:
        os.chdir(curPath)
        if e.message == "TIMEOUT":
            print("End %s == Run ACS Failed: [Timeout] ! %s" % (str(index), imageName))
            writelog("End %s == Run ACS Failed: [Timeout] ! %s" % (str(index), imageName))
            writehistory("End %s == Run ACS Failed: [Timeout] ! %s" % (str(index), imageName))        
        return False
        
def getPerformance(xmlfile):
    from xml.etree import ElementTree
    with open(xmlfile,'r') as f:
        root = ElementTree.fromstring(f.read())
        sub_nodes = root.findall("Test_Result")
        for sub_node in sub_nodes:
            lst_node = sub_node.findall("Test")
            for node in lst_node:
                score = node.find("Test_Comment").text.split("-")[2].split(":")[1].split(" ")[1]
                return float(score)
def getPower(xmlfile):
    from xml.etree import ElementTree
    result = ""
    with open(xmlfile,'r') as f:
        root = ElementTree.fromstring(f.read())
        sub_nodes = root.findall("Test_Result")
        if len(sub_nodes) > 0:
            result = sub_nodes[-1].findall("Test")[-1].findall("Test_Comment")[0].text
    return result
def getResult(type):
    rPath = "C:/Users/buildbot/Intel/ACS/acs_fwk/src/_Reports"
    curReport = [p for p in os.listdir(rPath) if os.path.isdir(os.path.join(rPath,p))][-1]
    rFile = os.path.join(rPath,curReport,"extTestResult.xml")
    if os.path.exists(rFile):
        if type == "power":
            return getPower(rFile)
        else:
            return getPerformance(rFile)
    return 0

def UpdateReleaseInfo(newversion,buildType):
    releases = map(lambda x:x.strip()+'\n',open("../conf/"+versionLog[buildType],'r').readlines())
    releases.append(newversion)    
    open("../conf/"+versionLog[buildType],'w').writelines(releases)

def checkNeedFlash(deviceType,buildType,comCode, imageName):
    if checkADB(deviceType,buildType,comCode):
        time.sleep(3)
        curImage = os.popen("adb shell getprop ro.build.version.incremental").read().strip()
        print curImage
        if imageName.find(curImage) > 0:
            return False
    return True
    
def SendEmail(msgTo,subject,mailContent):
    hostname = socket.gethostname()
    msg = MIMEMultipart()
    msg['From'] = 'zhaowangx.liang@intel.com'
    msg['To'] = msgTo
    msg['Cc'] = 'zhaowangx.liang@intel.com'
    msg['Subject'],content = subject + " in " + hostname,mailContent
    msg.attach(MIMEText(content, 'html', 'utf-8'))
    try:
        smtp = smtplib.SMTP('OutlookSH.intel.com', 25)
        smtp.starttls()
        smtp.login(msg['From'], password)
        smtp.sendmail(msg['From'], msg['To'].split(','), msg.as_string())
    except Exception,e:
        print e

def writelog(msg):
    dailylog.info(time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg)
def writehistory(msg):
    open("../log/history.log",'a').writelines(time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg + "\n")

def writeTaskList(version):
    tasklist = map(lambda x:x.strip(),open("../conf/tasklist.config",'r').readlines())
    if tasklist.count(version) == 0:
        open("../conf/tasklist.config",'a').writelines("\n"+version)
    
def runTask(task, imageName, caseType, deviceType,buildType, comCode,arg_campaign, arg_device, arg_benchcfg, arg_cr):
    try:
        UpdateTaskList(task)
        if flashImage(deviceType,buildType,comCode, imageName):
            runresult = False
            title = ""
            content = ""
            if runACS(arg_campaign, arg_device, arg_benchcfg, arg_cr, imageName, 1):
                title = "Task Run Success [%s]" % (task)
                content = "<label>Task %s Run Success!!!!</label><br/>" % (task)
                runresult = True
            else:
                title = "Task Run Failed [%s]" % (task)
                content = "<label>Task %s Run Failed!!!!</label>" % (task)
                runresult = False
            writehistory("")
            SendEmail("zhaowangx.liang@intel.com",title,content)
            return runresult
        else:
            return False
    except Exception, e:
        print("An unexpected error occurred when Running Task!  %s " % (e.message))
        writelog("An unexpected error occurred when Running Task!  %s " % (e.message))
        return False

def checkimagefile(imageName):
    pre = os.path.getsize(imageName)
    time.sleep(10)
    next = os.path.getsize(imageName)
    if pre == next:
        return True
    else:
        tempS = abs(10*(900*1024*1024-next)/(next - pre))
        print("Please wait %s s for next round:" % str(tempS))
        for i in range(tempS):
            time.sleep(1)
            PrintMessage("===== "+str(i)+" =====")
        print("")
        checkimagefile(imageName)

if __name__=='__main__':
    #checkADB("lte","M","COM1")
    #print checkNeedFlash("lte","M","COM1", "r2_sltmrdV12-flashfiles-M1l000457.zip")
    #print RunCmdWithTimeout.RunCommand("adb wait-for-device shell getprop ro.build.version.incremental",timeout_time=10,retry_count=0)
    #print Recover_DT("COM1","10","lte","M",3)
    #print RecoverDevice("COM1","10","lte","M")
    #print flashImage_PFT("lte","M","COM1", "../images/r2_sltmrdV12-flashfiles-M1l000488.zip")
    #flashImage_FT("lte","M","COM1", "../images/r2_sltmrdV12-flashfiles-M10000374.zip",1)
    
    #flashImage("lte","M","COM1", "../images/r2_sltmrdV12-flashfiles-M10000320.zip")
    #RestartDevices("COM1",10)
    #print Recover_PFT_ERASE("COM1",10,"lte","M",3)
    #subprocess.Popen("start")
    pass
