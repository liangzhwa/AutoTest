# -*- coding: utf8 -*-
import os
import sys
import time
from bs4 import BeautifulSoup
import logging as downloadlog
import urllib2
import smtplib
import json
import socket

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

curPath = os.path.split(os.path.realpath(__file__))[0]
os.chdir(curPath)

downloadlog.basicConfig(level=downloadlog.DEBUG,filename='../log/download.log', filemode='a')
conf = json.load(file("../conf/args.json"))
username = conf["username"]
password = conf["password"]
versionUrl = "https://buildbot.tl.intel.com/absp/builders/master-mergerequest?numbuilds=600"

template_url = conf["template_url_MR"]
MRList = ["4180","4179","4178","4177","4173","4170","4167"]
def getNewVersion():
    versionlist = []
    try:
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()    
        password_mgr.add_password(None, versionUrl, username, password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)
        response = urllib2.urlopen(versionUrl,timeout=180)
        soup_tb = BeautifulSoup(response.read(),"html.parser")
        list_tr = soup_tb.find_all('table')[0].find_all('tr')[1:]
        for tr in list_tr:
            cls_tmp = tr.find_all("td")[1]["class"][0]
            if cls_tmp == "success" or cls_tmp == "warnings":
                build = str(tr.find_all("td")[2].find("a").string[1:])
                if MRList.count(build) > 0:
                    versionlist.append(build)
        versionlist.reverse()
        return versionlist
    except Exception,e:
        print("|||||||||||||||An unexpected error occurred when get new version!" + e.message)
        writelog("|||||||||||||||An unexpected error occurred when get new version!" + e.message)
        versionlist.reverse()
        print versionlist
        return versionlist

def PrintMessage(msg):
    print >>sys.stderr,'\r',
    print >>sys.stderr,msg,

def download(deviceType,buildType,new_version,imageName,index, count,CallBackFunction=PrintMessage):
    if os.path.exists(imageName):
        return
    try:
        image_url = template_url[deviceType][buildType][index] % (new_version,new_version.zfill(6))
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()    
        password_mgr.add_password(None, image_url, username, password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

        response = urllib2.urlopen(image_url)
        outf = open(imageName,'wb')
        size = 0
        print('================>Download %s to %s \r'%(image_url,imageName))
        writelog('================>Download %s to %s \r'%(image_url,imageName))
        while True:
            tmp = response.read(1024*1024)
            if len(tmp) == 0:
                break
            outf.write(tmp)
            size += len(tmp)
            CallBackFunction('Download %d'%(size))
        print "\n"
        print('================Download Finished!')
        print("\n")
        writelog('================Download Finished!')
        writelog("\n")
        return True
    except Exception,e:
        print("|||||||||||||||(%s)Download image from %s failed! (%s)" % (str(index), image_url, e.message))
        writelog("|||||||||||||||(%s)Download image from %s failed! (%s)" % (str(index), image_url, e.message))
        index += 1
        if index > 2:
            index = 0
            count += 1
        if count < 3:
            download(deviceType,buildType,new_version,imageName,index, count)
        else:
            return False

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

def writeTaskList(version):
    tasklist = map(lambda x:x.strip(),open("../conf/tasklist.config",'r').readlines())
    if tasklist.count(version) == 0:
        open("../conf/tasklist.config",'a').writelines("\n"+version)
def writelog(msg):
    downloadlog.info(time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg)
    
if __name__=='__main__':
    os.system("title Download MergeRequest Image")
    deviceType = sys.argv[1]
    buildType = sys.argv[2]
    versionlist = getNewVersion()
    print(versionlist)
    for version in versionlist:
        imageName = "../images/" + template_url[deviceType][buildType][0].split("/")[-1] % (version.zfill(6))
        if download(deviceType,buildType,version,imageName,0, 1):
            writeTaskList("MR "+imageName.split("/")[-1])
