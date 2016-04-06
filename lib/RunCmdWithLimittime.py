#!/usr/bin/python2.7

import os
import signal
import subprocess
import threading
import time

import errors
import logger
import ProcManager

_abort_on_error = False
pipe = None

def SetAbortOnError(abort=True):
    global _abort_on_error
    _abort_on_error = abort

def RunCommand(cmd, limit_time=None, retry_count=3, return_output=None, stdin_input=None):
    result = None
    while True:
        try:
            result = RunOnce(cmd, limit_time=limit_time, return_output=return_output, stdin_input=stdin_input)
        except errors.WaitForResponseTimedOutError:
            if retry_count == 0:
                raise
            retry_count -= 1
        else:
            return result

def RunOnce(cmd, limit_time=None, return_output=None, stdin_input=None):
    start_time = time.time()
    so = []
    pid = []
    global _abort_on_error, error_occurred, pipe
    error_occurred = False
    
    def Run():
        global error_occurred
        if return_output:
            output_dest = subprocess.PIPE
        else:
            output_dest = None
        if stdin_input:
            stdin_dest = subprocess.PIPE
        else:
            stdin_dest = None
        pipe = subprocess.Popen(cmd,stdin=stdin_dest,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=True)
        pid.append(pipe.pid)
        try:
            returncode = pipe.poll()
            while returncode is None:
                line = pipe.stdout.readline()
                returncode = pipe.poll()
                line = line.strip()
                print line
                if line == "ACS OUTCOME: FAILURE":
                    so.append("ERROR_ACS")
            print returncode
            
            output = pipe.communicate()[0]
            if output is not None and len(output) > 0:
                so.append(output)
        except OSError, e:
            logger.SilentLog("failed to retrieve stdout from: %s" % cmd)
            logger.Log(e)
            so.append("ERROR")
            error_occurred = True
        if pipe.returncode:
            logger.SilentLog("Error: %s returned %d error code" %(cmd, pipe.returncode))
            error_occurred = True
    
    t = threading.Thread(target=Run)
    t.start()
    
    waittime = 0
    while t.isAlive():
        # Check the limit time
        if ((limit_time is not None) and (time.time() > start_time + limit_time)) or (len(so) > 0 and so[-1] == "ERROR_ACS"):
            try:
                if len(pid) > 0:
                    print "kill process %s" % (str(pid[0]))
                    ProcManager.killPid(pid[0])
            except OSError:
                print "=================== OS ERROR ==================="
                pass
            raise errors.WaitForResponseTimedOutError("TIMEOUT")
        time.sleep(1)
        waittime += 1
    t.join()
    output = "".join(so)
    if _abort_on_error and error_occurred:
        raise errors.AbortError(msg=output)
    return "".join(so)
    
if __name__ =='__main__':
    RunCommand("adb wait-for-device",limit_time=10,retry_count=0)
    pass