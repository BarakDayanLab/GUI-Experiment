#
# Copyright (C) 2015-2016 Ettore Landini
#
# This code is translated from another project of mines written in C#
#
# This is a python library for the NewPort Agilis controlle agUC2 and agUC8
#
# You can find another approach to this problem here: http://nullege.com/codes/show/src@t@e@terapy-2.00b6
#
#
#

## @package agPort
# This module contain classes that implements custom versions of python built-in serial port class
# for the agilis controllers 
#

from time import sleep
import serial as s
from datetime import datetime

## Documentatio for the AGPort class
#
# This class extend the python Serial class with some function that simplifies its use with the agilis controllers commands
class AGPort(s.Serial):
    
    ## Class constructor
    # @param portName The name of the virtual serial port of the chosen controller
    def __init__(self,portName = None):
        
        if portName == None:
            ## @var AGPort.soul
            self.soul = None
            return None
        try:
            super(AGPort,self).__init__(portName,921600,s.EIGHTBITS,s.PARITY_NONE,s.STOPBITS_ONE,timeout=1,xonxoff=True,rtscts=True)  # @@@
            self.soul = 'p'
        except Exception as e:
            print('I could not find or open the port you specified: {0}'.format(portName))
            self.soul = None
            return None
    
        
    def amInull(self):
        return self.soul is None
    
    
    def isAquery(self,command):
        
        if self.amInull():
            return False
        
        queryOnly=["?","PH","TE","TP","TS","VE"]
        command = command.upper()
        for q in queryOnly:
            if command.find(q) != -1:
                return True
        return False
    
    def sendString(self, command):

        # Send the command out
        self.write(bytes(command,'UTF-8'))
        sleep(0.1)

        # If we're dealing with a query, wait for result
        response = ''
        if self.isAquery(command):
            while True:
                response = self.readline()
                if len(response) > 0:
                    break
                sleep(0.1)

        str = '' if response == '' else response.decode('utf-8')
        return str

    def sendString2(self,command):
        
        response = ''
        bCommand = bytes(command,'UTF-8')

        self.write(bCommand)
        if self.isAquery(command):
            success = False
            for i in range(1,10):
                response = self.readline()
                if len(response) > 0:
                    success = True
                    break
            if not success:
                breakpoint()
        else:
            self.write(bytes('TE\r\n', 'UTF-8'))
            rc = self.readline()
            pass
        
        str = '' if response=='' else response.decode('utf-8')  # @@@
        return str
    
    
 