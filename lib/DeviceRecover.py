# -*- coding: utf8 -*-
import os
import sys
import subprocess
import time
import serial
import json
import RunCmdWithTimeout

conf = json.load(file("../conf/args.json"))
username = conf["username"]
password = conf["password"]

def ConnectUSB(comCode):
    print("Device not found, try to connect the USB...")
    ser = serial.Serial(str(comCode), 19200, timeout=5)
    ser.write("j")
    ser.close()
    time.sleep(3)
def RestartDevices(comCode,cutpowertime):
    print("Device not found, cut the device's power by press power-key for %s s..." % (str(cutpowertime)))
    ser = serial.Serial(str(comCode), 19200, timeout=5)
    ser.write("i")
    time.sleep(cutpowertime)
    ser.write("s")
    time.sleep(3)
    print("Press power-key for 5 s to restart the device..")
    ser.write("i")
    time.sleep(5)
    ser.write("s")
    print "Please wait 180S for device restart..."
    for i in range(180):
        PrintMessage("====== %s ======" % (str(i)))
        time.sleep(1)
    RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=120,retry_count=0)
    ser.close()
def RecoverDevice(comCode,cutpowertime,deviceType,buildType):
    print("<<<<<<<<<<<Device not found, Recover Device: ")
    if Recover_PFT_ERASE(comCode,cutpowertime,deviceType,buildType,3):
        return True
    if Recover_PFT(comCode,cutpowertime,deviceType,buildType,3):
        return True
        
    if Recover_FT(comCode,cutpowertime,deviceType,buildType,1,3):
        return True
    if Recover_FT(comCode,cutpowertime,deviceType,buildType,0,3):
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
    
    for i in range(retry_count):
        subprocess.Popen("python CutPower.py %s %s" % (comCode,cutpowertime))
        if os.system(dtCmd) == 0:
            print "Please wait 120S for device first starting..."
            for i in range(120):
                PrintMessage("====== %s ======" % (str(i)))
                time.sleep(1)
            RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=180,retry_count=0)
            recover_result = True
            break
    print("<<<<<<<<<<<Recover Device End: Method: Recover_PFT; Image: %s; Result: %s" % (recoverImage,str(recover_result)))
    return recover_result
def Recover_PFT(comCode,cutpowertime,deviceType,buildType,retry_count):
    recover_result = False
    recoverImage = conf["recoverImage"][deviceType][buildType]
    flashcmd = conf["flashcmd"][deviceType] + recoverImage
    
    print("<<<<<<<<<<<Recover Device Start: Method: Recover_PFT; Image: " + recoverImage)
    
    for i in range(retry_count):
        subprocess.Popen("python CutPower.py %s %s" % (comCode,cutpowertime))
        if os.system(flashcmd) == 0:
            print "Please wait 120S for device first starting..."
            for i in range(120):
                PrintMessage("====== %s ======" % (str(i)))
                time.sleep(1)
            RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=180,retry_count=0)
            recover_result = True
            break
    
    print("<<<<<<<<<<<Recover Device End: Method: Recover_PFT; Image: %s; Result: %s" % (recoverImage,str(recover_result)))
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
            shell.Run("C:/FlashTool/FlashTool_E2.exe FlashTool_E2.ini -f")
            win32api.Sleep(3000)
            shell.AppActivate("Download")
            win32api.Sleep(1000)
            shell.SendKeys("{ENTER}")
            win32api.Sleep(1000)
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
                os.system("taskkill /F /IM FlashTool_E2.exe")
            else:
                print("Build version checked Failed!")
                os.system("taskkill /F /IM FlashTool_E2.exe")
                continue
            #after flash, reboot device
            bootmode = os.popen("adb shell getprop ro.bootmode").read().strip()
            if bootmode == "normal" or bootmode == "unknown":
                os.system("adb reboot")
                time.sleep(180)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=120,retry_count=0)
            else:
                RestartDevices(comCode,10)
                os.system("adb reboot")
                time.sleep(180)
                RunCmdWithTimeout.RunCommand("adb wait-for-device",timeout_time=120,retry_count=0)
                
            if checkADB(deviceType,buildType,comCode):
                print(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Success!" % (str(i),erasemode,recoverImage))
                return True
            else:
                print(">>>>>>>>>>(%s) ; Method: flashImage_FT(erase-mode=%s) ; Flash Image finished[%s]. ADB Check Failed!" % (str(i),erasemode,recoverImage))
        return False
    except Exception, e:
        print("Method: flashImage_FT(erase-mode=%s) ;An unexpected error occurred when flash image: %s.   %s" % (recoverImage,erasemode,e.message))
        return False


def checkADB(deviceType,buildType,comCode):
    curBuild = ""
    result = False
    cutpowertime = int(conf["cutpowertime"])
    restarttimes = int(conf["restarttimes"])
    
    curBuild = os.popen("adb shell getprop ro.build.version.incremental").read().strip()
    if len(curBuild) != 9:
        ConnectUSB(comCode)
        curBuild = os.popen("adb shell getprop ro.build.version.incremental").read()
        if len(curBuild) != 9:
            for i in range(restarttimes):
                RestartDevices(comCode,cutpowertime)
                curBuild = os.popen("adb shell getprop ro.build.version.incremental").read()
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


def checkNeedUnzip(imageName):
    if os.path.exists(imageName.replace(".zip","") + "/flash.json"):
        confFile = file(imageName.replace(".zip","") + "/flash.json")
        conf = json.load(confFile)
        confFile.close()
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

if __name__=='__main__':
    deviceType = sys.argv[1]
    buildType = sys.argv[2]
    print RecoverDevice("COM12",12,deviceType,buildType)
    pass
