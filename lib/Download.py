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
versionUrl = conf["versionUrl"]
versionLog = conf["versionLog"]
template_url = conf["template_url"]

def getNewVersion(buildType):
    versionlist = []
    try:
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, versionUrl[buildType], username, password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)
        response = urllib2.urlopen(versionUrl[buildType],timeout=180)
        soup_tb = BeautifulSoup(response.read(),"html.parser")
        tdlist = soup_tb.find_all("table",attrs={"class":["info"]})[0].find_all(["tr","td"],attrs={"class":["warnings","success"]})
        for td in tdlist:
            runedlist = map(lambda x:x.strip(),open("../conf/"+versionLog[buildType],'r').readlines())
            version = td.find_next_sibling().text.replace("#","")
            if len(runedlist) == 0 or int(version) > int(runedlist[-1]):
               versionlist.append(version)
        versionlist.reverse()
        return versionlist
    except Exception,e:
        print("|||||||||||||||An unexpected error occurred when get new version!\n" + str(e.reason))
        writelog("|||||||||||||||An unexpected error occurred when get new version!\n" + str(e.reason))
        versionlist.reverse()
        return versionlist

def PrintMessage(msg):
    print >>sys.stderr,'\r',
    print >>sys.stderr,msg,

def download(deviceType,buildType,new_version,imageName,index, count,CallBackFunction=PrintMessage):
    if os.path.exists(imageName):
        return True
    image_url = template_url[deviceType][buildType][index] % (new_version,new_version.zfill(6))
    try:        
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
    tasklist = map(lambda x:x.strip()+'\n',open("../conf/tasklist.config",'r').readlines())
    if tasklist.count(version+'\n') == 0:
        tasklist.append(version)
        open("../conf/tasklist.config",'w').writelines(tasklist)
def writelog(msg):
    downloadlog.info(time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg)
    
if __name__=='__main__':
    os.system("title Download Image")
    deviceType = sys.argv[1]
    buildType = sys.argv[2]
    while 1:
        versionlist = getNewVersion(buildType)
        print versionlist
        for version in versionlist:
            imageName = "../images/" + conf["template_url"][deviceType][buildType][0].split("/")[-1] % (version.zfill(6))
            if download(deviceType,buildType,version,imageName,0, 1):
                writeTaskList("LB "+imageName.split("/")[-1])
        print("Please wait 300S for next round to download...")
        for i in range(300):
            PrintMessage("====== %s ======" % (str(i)))
            time.sleep(1)
