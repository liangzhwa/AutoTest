# -*- coding: utf-8 -*-
import RunDaily
import sys,os,time,subprocess,json
import datetime

conf = json.load(file("../conf/args.json"))
def StartRun(caseType, deviceType, buildType,comCode,arg_campaign, arg_device, arg_benchcfg, arg_cr):
    
    while 1:
        if datetime.datetime.now().hour > 15: continue
             
        tasklist = RunDaily.getTaskList()
        if len(tasklist) > 0:
            imageTpl = conf["imageTpl"][deviceType][buildType]
            for task in tasklist:
                imageName = ""
                if len(task.split(" ")) != 2:
                    continue

                if task.startswith("IL") or task.startswith("LB") or task.startswith("MR") or task.startswith("WB"):
                    imageName = "../images/" + task.split(" ")[1]
                    if not os.path.exists(imageName):
                        print("image %s not exists!"%(imageName))
                        RunDaily.writelog("image %s not exists!"%(imageName))
                        continue
                else:
                    local = task.split(" ")[0]
                    ebcode = task.split(" ")[1].strip()
                    imageURL = imageTpl % (local,ebcode,ebcode.zfill(6))
                    imageName = "../images/" + imageURL.split("/")[-1]
                    if not os.path.exists(imageName):
                        RunDaily.downloadbyurl(imageURL,imageName)
                #self.listRunLog.addItem("[ACS Start] Task:" + task)
                time.sleep(10)
                result = RunDaily.runTask(task, imageName, caseType, deviceType, buildType,comCode,arg_campaign, arg_device, arg_benchcfg, arg_cr)
                msg = "Success" if result else "Failed"
                #self.listRunLog.addItem("[ACS Run Finished] Task: %s Result: %s" % (task, msg))
                if task.startswith("LB"):
                    RunDaily.UpdateReleaseInfo(task.split(" ")[1][-10:-4].lstrip("0"),buildType)
        print "Please wait 360S for next round to run..."
        for i in range(360):
            PrintMessage("====== %s ======" % (str(i)))
            time.sleep(1)

def PrintMessage(msg):
    print >>sys.stderr,'\r',
    print >>sys.stderr,msg,
        
if __name__=='__main__':
    caseType = sys.argv[1]
    deviceType = sys.argv[2]
    buildType = sys.argv[3]
    comCode = sys.argv[4]
    arg_campaign = sys.argv[5]
    arg_device = sys.argv[6]
    arg_benchcfg = sys.argv[7]
    arg_cr = sys.argv[8]
    
    StartRun(caseType, deviceType, buildType,comCode,arg_campaign, arg_device, arg_benchcfg, arg_cr)