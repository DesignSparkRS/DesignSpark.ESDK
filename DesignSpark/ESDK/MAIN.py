# Copyright (c) 2021 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK Main board interface
'''

import smbus2
import toml
import threading
import re
import geohash
from gpsdclient import GPSDClient
from . import AppLogger
from . import MAIN, THV, CO2, PM2

possibleModules = {
    "THV": 0x44, 
    "CO2": 0x62, 
    "PM2": 0x69
}

moduleTypeDict = {
    'THV': THV,
    'CO2': CO2,
    'PM2': PM2
}

strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")

class ModMAIN:
    def __init__(self, debug=False, configFile='/boot/aq/aq.toml'):
        self.logger = AppLogger.getLogger(__name__, debug)
        try:
            self.bus = smbus2.SMBus(1)
        except Exception as e:
            raise e

        self.moduleNames = []
        self.sensorModules = {}
        self.sensorData = {}
        self.configFile = configFile
        self.configDict = {}
        self.location = {}
        self._parseConfig()

    def _parseConfig(self):
        """ Parse config when mainboard initialised """
        try:
            with open(self.configFile) as configFileHandle:
                self.configDict = toml.loads(configFileHandle.read())
            self.logger.debug("Parsed config {}".format(self.configDict))
        except Exception as e:
            self.logger.error("Could not parse config, reason {}".format(e))
            raise e

        if self.configDict['ESDK']['gps'] is not None:
            if self.configDict['ESDK']['gps'] == True:
                self.logger.info("GPS is enabled")
                self.gps = GPSDClient(host="localhost")
                gpsHandlerThreadHandle = threading.Thread(target=self._gpsHandlerThread, daemon=True)
                gpsHandlerThreadHandle.name = "gpsHandlerThread"
                gpsHandlerThreadHandle.start()

    def _gpsHandlerThread(self):
        """ Thread for polling GPS """
        self.logger.debug("Started GPS handling thread")
        while True:
            try:
                for result in self.gps.dict_stream():
                    if result["class"] == "TPV":
                        self.location['lat'] = result.get("lat", "n/a")
                        self.location['lon'] = result.get("lon", "n/a")
                        self.logger.debug("GPS location {}".format(self.location))
            except Exception as e:
                self.logger.error("Error getting GPS location, reason {}".format(e))

    def _probeModules(self):
        """ Probe I2C bus to attempt to find sensor modules """
        self.moduleNames.clear()
        self.logger.debug("Starting module probe")
        for module, addr in possibleModules.items():
            try:
                self.bus.write_byte(addr, 0)
                self.moduleNames.append(module)
            except Exception as e:
                # Ignore any that fail - the modules aren't present on the bus
                pass
        self.logger.info("Found modules {}".format(self.moduleNames))

    def getMqttConfig(self):
        """ Return a dictionary containing MQTT config """
        return self.configDict["mqtt"]

    def getPrometheusConfig(self):
        """ Return a dictionary containing Prometheus config, and friendly name """
        configDict = {}
        configDict.update(self.configDict["prometheus"])
        configDict.update({"friendlyname":self.configDict["ESDK"]["friendlyname"]})
        return(configDict)

    def getLocation(self):
        """ Return a geohash of either actual GPS location, or config file location """
        if self.configDict['ESDK']['gps'] == False or self.configDict['ESDK']['gps'] is None:
            location = {}
            location['geohash'] = geohash.encode(self.configDict['ESDK']['latitude'], self.configDict['ESDK']['longitude'])
            return location

        if self.configDict['ESDK']['gps'] == True:
            location = {}
            location['geohash'] = geohash.encode(self.location['lat'], self.location['lon'])
            return location

    def createModules(self):
        """ Create dictionary of modules ready for later use """
        self._probeModules()
        self.logger.debug("Creating module objects")
        for moduleName in self.moduleNames:
            try:
                if moduleName == "THV":
                    self.sensorModules[moduleName] = moduleTypeDict[moduleName].ModTHV()

                if moduleName == "CO2":
                    self.sensorModules[moduleName] = moduleTypeDict[moduleName].ModCO2()

                if moduleName == "PM2":
                    self.sensorModules[moduleName] = moduleTypeDict[moduleName].ModPM2()
            except Exception as e:
                self.logger.error("Could not create module {}, reason {}".format(moduleName, e))

    def readAllModules(self):
        """ Try to read all sensor modules and return a dictionary of values """
        try:
            for name, module in self.sensorModules.items():
                self.logger.debug("Trying to read {}".format(name))
                data = module.readSensors()
                if data != -1:
                    self.sensorData.update(data)
        except Exception as e:
            self.logger.error("Could not read module {}, reason {}".format(name, e))

        self.logger.debug("Sensor data {}".format(self.sensorData))
        return self.sensorData

    def getSerialNumber(self):
        """ Try to read the Raspberry Pi serial number to use as HWID """
        try:
            serialNumber = {}
            with open('/sys/firmware/devicetree/base/serial-number') as f:
                serialNumber['hardwareId'] = "RPI{}".format(strip_unicode.sub('',f.read()))
                self.logger.info("Hardware ID is {}".format(serialNumber['hardwareId']))
            return serialNumber
        except Exception as e:
            self.logger.error("Could not retrieve serial number, reason {}".format(e))
            return -1

    def getFriendlyName(self):
        """ Return the string of the device friendly name """
        return self.configDict['ESDK']['friendlyname']

    def getCsvEnabled(self):
        """ Return CSV enabled value """
        if self.configDict['local']['csv'] is not None:
            return self.configDict['local']['csv']
        else:
            return False