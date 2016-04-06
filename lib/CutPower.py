# -*- coding: utf8 -*-
import sys,subprocess
import serial
import time

#iocard: i:power-key on; s:power-key off; j:usb on; t:usb off
def Run(comCode,cutpowertime):
    print("Cut the device's power by press power-key for %s s..." % (cutpowertime))
    ser = serial.Serial(str(comCode), 19200, timeout=5)
    ser.write("t")
    time.sleep(1)
    ser.write("i")
    time.sleep(int(cutpowertime))
    ser.write("j")
    time.sleep(2)
    ser.write("s")
    ser.close()
    print("Cut power done")

if __name__=='__main__':
    time.sleep(10)
    comCode = sys.argv[1]
    cutpowertime = sys.argv[2]
    Run(comCode,cutpowertime)