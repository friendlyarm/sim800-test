#!/usr/bin/env python
#
# sim800_test.py
# test if sim800 On/Off/reboot correctly, and UART/AT works normally
#  
# Author : 
# Date   : 

# Import required Python libraries
import time, getopt, sys
import serial
import RPi.GPIO as GPIO

# Set up the connection to the module
gprs = serial.Serial(port="/dev/ttyS3",baudrate=115200,timeout=2,rtscts=0,xonxoff=0)

tmReboot = int(time.time())
PHONE='123456789'
pinNum = '1234'
OPERATOR = 'cmcc'  # China Mobile Communication Corporation
#OPERATOR = 'cucc'  # China Union Communication Corporation
WEBSITE="http://www.baidu.com/"

GPIO.cleanup()
LED = 9   #red, SIM800 power state
GSM_PWR = 11  # SIM800 PWRKEY, reboot
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(GSM_PWR,GPIO.IN)

GPIO.setup(LED, GPIO.OUT)
GPIO.output(LED, GPIO.LOW)

def ledOff():
    GPIO.output(LED, True)
    time.sleep(0.2)
    
def ledOn():
    GPIO.output(LED, False)
    time.sleep(0.2)

def readRespMsg(wtTime, expectRtnCode = 'OK'):
    answered = 0
    returnStr = ''
    preTime = int(time.time())
    
    while (answered==0) and ((int(time.time())-preTime)<wtTime):
        returnStr += gprs.read(gprs.inWaiting())        
        if expectRtnCode in returnStr:
            answered = 1
        time.sleep(0.2)
    print '--->Receive: '+returnStr
    return returnStr

# This sends the command to the module
def sendAtCmd(cmd):
    snd = 'AT'+cmd+'\r'
    print("--->Send: "+snd)
    gprs.write(snd)
    time.sleep(0.2)

def testAt():
    b_Boot = False
    for i in range(3):
        sendAtCmd("")
        rtn = readRespMsg(0.8, "OK")                
        if "OK" in rtn:
            b_Boot = True            
            break
        time.sleep(0.2)
    return b_Boot    

def testSIMCard():
    print ("Checking SIM card...")
    sendAtCmd('+CSMINS?')
    rtn = readRespMsg(5, "OK")                
    if ",1" in rtn:
        print("SIM inserted")
        return True
    elif ",0" in rtn:
        print("SIM NOT inserted")
        return False

def cmdCSQ():
    sendAtCmd("+CSQ")
    readRespMsg(5, "OK")

def cmdCFUN():
    result = False
    sendAtCmd("+CFUN?")
    #by default, waiting for OK
    rtn = readRespMsg(5)

def cmdCPIN():
    print ("checking PIN...")
    result = False
    sendAtCmd("+CPIN?")
    #by default, waiting for OK
    rtn = readRespMsg(5)
    
    if "+CPIN: READY" in rtn:
        result = True
    elif "+CPIN: SIM PIN" in rtn:
        # set pin of sim card
        print("set PIN to "+pinNum)
        #sendAtCmd('+CPIN='+pinNum)
        if '+CPIN: READY' in readRespMsg(10, "+CPIN: READY"):
            result = True
        else:
            print("PIN error")
    return result

def cmdCOPS():
    print ("Checking the operator...")
    opsCMD = '+COPS=0,1,"' + OPERATOR +'"'
    sendAtCmd(opsCMD)
    if 'OK' in readRespMsg(10):
        return True
    else:
        return False

def powerOn():
    print ("Powering on...")
    global tmReboot
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GSM_PWR,GPIO.OUT)
    GPIO.output(GSM_PWR, GPIO.LOW)
    time.sleep(1*2)
    GPIO.output(GSM_PWR, GPIO.HIGH)
    time.sleep(2*2)
    print ("Power On @"+time.ctime(tmReboot))

    # sim card may not ready
    time.sleep(5)
    
def powerOff():
    print ("Powering off...")
    tm = int(time.time())    
    sendAtCmd("+CPOWD=1")
    rtn = readRespMsg(10, "NORMAL POWER DOWN")
    tmDown = int(time.time())
    
    if "NORMAL POWER DOWN" in rtn:
        print ("Power off@ "+time.ctime(tmDown)+", use "+str(tmDown-tm)+" sec.")
        GPIO.setup(GSM_PWR, GPIO.IN)
    else:
        print ("Power already off?")

        

def setAPN(): #Activate bearer profile
    res = False  
    sendAtCmd('+SAPBR=3,1,"APN",cmnet')
    rtn = readRespMsg(5, "OK")

    if "OK" in rtn:
        print ("already activate bearer profile")
        res = True    
    else:
        print ("activate bearer profile error")
    return res

def setPhoneNumber(phonenumber): 
    res = False  
    sendAtCmd('+SAPBR=3,1,"PHONENUM","'+phonenumber+'"')
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
        print ("already set PhoneNumber")
        res = True    
    else:
        print ("setPhoneNumber error")
    return res

def activeDataConnection(): 
    res = False  
    sendAtCmd('+SAPBR=1,1')
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
        print ("already actived data connection")
        res = True    
    else:
        print ("Data connection may be actived before?")
    time.sleep(2)
    return res

def getIP(): 
    res = False  
    sendAtCmd('+SAPBR=2,1')
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
	#print(rtn.split('"'))
        rtn = rtn.split('"')[1]
        print ("IP is:"+rtn)
        res = True
    else:
        print ("Get IP error")
    return res

def closeHTTPService():
    res = False  
    sendAtCmd('+HTTPTERM')
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
        print ("already Terminate HTTP Service")
        res = True    
    else:
        print ("HTTP service may be terminated before?")
    return res

def initHTTPService(cmd): #Initialize HTTP Service
    res = False  
    sendAtCmd('+HTTPINIT')
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
        print ("already Initialize HTTP Service")
        res = True    
    else:
        print ("HTTP service may be inited before?")
    return res

def setHTTPParameters(URL,web): #Set HTTP Parameters Value
    res = False  
    sendAtCmd('+HTTPPARA="'+URL+'","'+web+'"')
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
        print ("already Set HTTP Parameters Value")
        res = True    
    else:
        print ("Set HTTP Parameters Value error")
    return res

def activeHTTPService(way): #active HTTP Service
    #0---get;1---psot;2---head
    res = False  
    sendAtCmd('+HTTPACTION='+str(way))
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
        print ("already active HTTP Service")
        res = True    
    else:
        print ("active HTTP Service error")
    return res

def getHTTPData(start,lenth): #get  HTTP data
    res = "begin"
    sendAtCmd('+HTTPREAD='+str(start)+','+str(lenth))
    rtn = readRespMsg(10, "HTTPREAD")
    if "+HTTPACTION: 0,200" in rtn:
        res = "finish"
    else:
        res = "waiting"
    return res

def closeBearer(): 
    res = False  
    sendAtCmd('+SAPBR=0,1')
    rtn = readRespMsg(5, "OK")
    if "OK" in rtn:
        print ("already Close bearer")
        res = True  
    else:
        print ("Close bearer error")
    return res


def test(args):
    if len(args) != 7:
        print './sim800c-test.py -p <phone_number> -o <operator, cmcc> -w <website>'
        sys.exit(2)

    args.pop(0)
    try:
        optlist, args = getopt.getopt(args, 'p:o:w:')
    except getopt.GetoptError:
        print './sim800c-test.py -p <phone_number> -o <operator, cmcc> -w <website>'
        sys.exit(2)

    for opt, arg in optlist:
        global PHONE, OPERATOR, WEBSITE
        if opt == '-h':
            print './sim800c-test.py -p <phone_number> -o <operator, cmcc> -w <website>'
            sys.exit()
        elif opt == '-p':
            PHONE=arg
        elif opt == '-o':
            OPERATOR=arg
        elif opt == '-w':
            WEBSITE=arg
    
    try:
        print "Checking power state"
        if testAt():
            print ("Already power on")
        else: 
            powerOn()

        if not testAt():
            print "Failed to power on"
        else:
            if testSIMCard() == False:
                return
            cmdCSQ()
            cmdCFUN()
            if cmdCPIN() == False:
                return
            if cmdCOPS() == False:
                return
            if setAPN() == False:
                return
            if setPhoneNumber(PHONE) == False:
                return
            activeDataConnection()
            if getIP() == False:
                return
            initHTTPService('+HTTPINIT')
            if setHTTPParameters("CID","1") == False:
                return
            if setHTTPParameters("URL",WEBSITE) == False:
                return
            if activeHTTPService(0) == False:
                return
            wtTime = 0
            lenth = 1024
            ret = getHTTPData(1,lenth)
            while ret == "waiting":
                wtTime += 5
                print("Receiving data(%d second)" % wtTime)
                time.sleep(wtTime)
                ret = getHTTPData(1,lenth)
	        
            #To do further PPP dialing up test: ppp_test.py
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
    except RuntimeError:
        print "Runtime error"
    except Exception as e:
        print ("Except=>%s" %e)
    finally:
        print ("\nExiting....")
        ledOff()
        closeHTTPService()
        closeBearer()
        powerOff()

if __name__ == "__main__":
    test(sys.argv)

