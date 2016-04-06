# -*- coding: utf8 -*-
import os
import sys
import time
from bs4 import BeautifulSoup
import logging as bisectlog
import ftplib
import serial
import urllib2
import json
import traceback

curPath = os.path.split(os.path.realpath(__file__))[0]
acsPath = "C:/Users/buildbot/Intel/ACS/acs_fwk/src"
os.chdir(curPath)

bisectlog.basicConfig(level=bisectlog.DEBUG,filename='../log/bisect.log', filemode='a')
confFile = file("../conf/args.json")
conf = json.load(confFile)
confFile.close()
caseInfo = conf["caseInfo"]
localImage = conf["localImage"]
i_name = conf["i_name"]
orgUrl = conf["orgUrl"]
OrignList = conf["OrignList"]

acsCmd_template = """C:/Python27/python.exe "C:/Users/buildbot/Intel/ACS/acs_fwk/src/ACS.py" -c "%s" -d %s -b "%s" %s"""

def checkADB(comCode):
    while 1:
        if os.system("adb root")==0:
            print "root success!"
        time.sleep(1)
        devices = os.popen("adb devices")
        if len(devices.readlines()) > 2:
            break
        else:
            ser = serial.Serial(str(comCode), 19200, timeout=5)
            ser.write("j")
            ser.close()
    print "adb ok!"
def download(imageName,buildcode, deviceType):
    print "-------------------"
    print imageName + "    " + buildcode
    print "-------------------"
    if not os.path.exists("../images/" + imageName):
        try:
            writelog("download image from ftp: " + imageName)
            print("download image from ftp:" + imageName)
            ftp = ftplib.FTP()
            ftp.connect("10.239.93.77",21)
            ftp.login("chuzhul","123")
            ftp.set_pasv(0)
            ftp.cwd(localImage[deviceType])
            f = open("../images/"+imageName, 'wb')
            ftp.retrbinary('RETR ' + imageName , f.write , 1024)
            f.close()
        except Exception:
            print traceback.format_exc()
            f.close()
            if os.path.exists("../images/" + imageName):
                os.remove("../images/" + imageName)
            image_rl = orgUrl[deviceType] % (buildcode,buildcode.zfill(6))
            print "download image from url: "+image_rl
            writelog("download image from url: " + image_rl)
            downloadfromorg(image_rl,imageName)
        finally:
            ftp.close()
def PrintMessage(msg):
    print >>sys.stderr,'\r',
    print >>sys.stderr,msg,
def downloadfromorg(image_url,imageName,CallBackFunction=PrintMessage):
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()    
    password_mgr.add_password(None, image_url, "zliangx", "lzw,123,1")
    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)
    urllib2.install_opener(opener)
    response = urllib2.urlopen(image_url)
    outf = open("../images/"+imageName, 'wb')
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
def getOrignList(deviceType):
    orginList = []
    url = OrignList[deviceType]
    p = urllib2.HTTPPasswordMgrWithDefaultRealm()
    p.add_password(None, url, 'zliangx', 'lzw,123,1')
    handler = urllib2.HTTPBasicAuthHandler(p)
    opener = urllib2.build_opener(handler)
    urllib2.install_opener(opener)
    content = urllib2.urlopen(url).read()    
    soup_tb = BeautifulSoup(content,"lxml")
    list_tr = soup_tb.find_all('table')[0].find_all('tr')[1:]
    for tr in list_tr:
        cls_tmp = tr.find_all("td")[1]["class"][0]
        if cls_tmp == "success" or cls_tmp == "warnings":
            build =  tr.find_all("td")[2].find("a").string[1:]
            orginList.append(build)
    orginList.reverse()
    print orginList
    return orginList
def getBisectList(orginList,start,end):
    if start not in orginList or end not in orginList:
        return []
    else:
        return orginList[orginList.index(start)+1:orginList.index(end)]
def getBisectPoint(list):
    if len(list) <= 0:
        return None
    if len(list) % 2 == 0:
        return list[len(list)/2]
    if len(list) % 2 != 0:
        return list[(len(list)-1)/2]
def unzipImage(imageName):
    if checkNeedUnzip(imageName):
        import zipfile
        if not os.path.exists("../images/" + imageName):
            print "Image File : %s not exists." % (imageName)
            return
        if not os.path.exists("C:/Temp/flashimage"):
            os.mkdir("C:/Temp/flashimage")
        for flsFile in os.listdir("C:/Temp/flashimage"):
            if os.path.isfile(flsFile):
                try:
                    os.remove(flsFile)
                except:
                    pass
        zfile = zipfile.ZipFile('../images/'+imageName,'r')
        for filename in zfile.namelist():
            zfile.extract(filename,"C:/Temp/flashimage")
            
def flashImage(deviceType,comCode, imageName):
    if checkNeedFlash(imageName,comCode):
        writelog("flash image: " + imageName)
        if not os.path.exists("../images/" + imageName):
            print "Image File : %s not exists." % (imageName)
            return False
        checkADB(comCode)
        flsFile = filter(lambda x: x!="flash.json" and x!="mvconfigs",os.listdir("C:/Temp/flashimage/"))
        flsFile = map(lambda x: "c:/Temp/flashimage/"+x,flsFile)
        flashcmd = conf["flashcmd"][deviceType] + " ".join(flsFile)
        if os.system(flashcmd) == 0:
            print "Please wait 360S for device first starting..."
            for i in range(360):
                PrintMessage("====== %s ======" % (str(i)))
                time.sleep(1)
            checkADB(comCode)
            return True
        return False
    else:
        return True
def runACS(arg_campaign, arg_device, arg_benchcfg, arg_cr):
    os.chdir(acsPath)
    acsCmd = acsCmd_template % (arg_campaign,arg_device,arg_benchcfg,arg_cr)
    acsResult = os.system(acsCmd)
    os.chdir(acsPath)
    if acsResult == 0:
        return True
    else:
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
            result = sub_nodes.findall("Test")[-1].findall("Test_Result").text
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

def checkNeedUnzip(imageName):
    if os.path.exists("C:/Temp/flashimage/flash.json"):
        confFile = file("C:/Temp/flashimage/flash.json")
        conf = json.load(confFile)
        confFile.close()
        if imageName.find(conf["build_info"]["ro.build.version.incremental"]) > 0:
            return False
    return True

def checkNeedFlash(imageName,comCode):
    checkADB(comCode)
    curImage = os.popen("adb shell getprop ro.build.version.incremental").read().strip()
    if imageName.find(curImage) > 0:
        return False
    return True
    
def Start(type, deviceType, comCode, arg_campaign, arg_device, arg_benchcfg,arg_cr,  sBuild,eBuild, caseNo, sValue, eValue):
    print("Bisect start --- Case:%s,release: bettwen %s(%s) and %s(%s) ---" % (caseInfo[type][caseNo]["campaign"],sBuild,str(sValue),eBuild,str(eValue)))
    writelog("Bisect start --- Case:%s,release: bettwen %s(%s) and %s(%s) ---" % (caseInfo[type][caseNo]["campaign"],sBuild,str(sValue),eBuild,str(eValue)))
    sImageName = i_name[deviceType] % (sBuild.zfill(6))
    if sValue == -1 or eValue == -1:
        download(sImageName,sBuild, deviceType)
        unzipImage(sImageName)
        if flashImage(deviceType,comCode, sImageName):
            runACS(arg_campaign, arg_device, arg_benchcfg,arg_cr)
            sValue = getResult(type)
            if sValue == 0:
                print("build(%s) run failed."%(sImageName))
                return
        else:
            print("Flash Image failed: %s" % (sImageName))
            writelog("Flash Image failed: %s" % (sImageName))
            return
        eImageName = i_name[deviceType] % (eBuild.zfill(6))
        download(eImageName,eBuild, deviceType)
        unzipImage(eImageName)
        if flashImage(deviceType,comCode, eImageName):
            runACS(arg_campaign, arg_device, arg_benchcfg,arg_cr)
            eValue = getResult(type)
            if eValue == 0:
                print("build(%s) run failed."%(eImageName))
                return
        else:
            print("Flash Image failed: %s" % (eImageName))
            writelog("Flash Image failed: %s" % (eImageName))
            return
        print("re-Run { %s:%s , %s:%s }" % (sBuild,sValue,str(eBuild),(eValue)))
        writelog("re-Run { %s:%s , %s:%s }" % (sBuild,sValue,str(eBuild),(eValue)))

    orignList = getOrignList(deviceType)
    bisectList = getBisectList(orignList,sBuild,eBuild)
    print("orignList: " + ",".join(orignList))
    writelog("orignList: " + ",".join(orignList))
    print("bisectList: " + ",".join(bisectList))
    writelog("bisectList: " + ",".join(bisectList))
    while len(bisectList) > 1:
        build = getBisectPoint(bisectList)
        imageName = i_name[deviceType] % (build.zfill(6))
        try:
            download(imageName,build, deviceType)
        except:
            print("download image:%s failed!"%(imageName))
            writelog("download image:%s failed!"%(imageName))
            if os.path.exists("../images/"+imageName):
                os.remove("../images/"+imageName)
            bisectList.remove(build)
            continue
        unzipImage(imageName)
        if flashImage(deviceType,comCode, imageName):
            runACS(arg_campaign, arg_device, arg_benchcfg,arg_cr)
            value = getResult(type)
            if value == 0:
                print("build(%s) run failed."%(imageName))
                return
            print("bisect Point { %s:%s }" % (build,value))
            writelog("bisect Point { %s:%s }" % (build,value))
            if(caseInfo[type][caseNo]["largeisbetter"] == 1):
                if (sValue-value)/sValue > caseInfo[type][caseNo]["margin"]:
                    bisectList = bisectList[0:bisectList.index(build)]
                elif (eValue-value)/eValue > caseInfo[type][caseNo]["margin"]:
                    bisectList = bisectList[bisectList.index(build):]
                else:
                    bisectList = []
            else:
                if (value-sValue)/value > caseInfo[type][caseNo]["margin"]:
                    bisectList = bisectList[0:bisectList.index(build)]
                elif (value-eValue)/value > caseInfo[type][caseNo]["margin"]:
                    bisectList = bisectList[bisectList.index(build):]
                else:
                    bisectList = []
        else:
            print("Flash Image failed: %s" % (imageName))
            writelog("Flash Image failed: %s" % (imageName))
            break
    print("Bisect end --- regression:  ---")
    writelog("Bisect end --- regression:  ---")
    
def PrintMessage(msg):
    print >>sys.stderr,'\r',
    print >>sys.stderr,msg,
def writelog(msg):
    bisectlog.info(time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg)

if __name__=='__main__':
    #unzipImage("r2_s3gr10m6s-flashfiles-L1l000215.zip")
    #print flashImage("r2_s3gr10m6s-flashfiles-L1m001700.zip")
    #runACS(caseInfo["1"]["campaign"])
    #getResult()
    download("r2_s3gr10m6s-flashfiles-L1m001700.zip","1700")
    #Start("perf","1435","1445","13",331, 380)
