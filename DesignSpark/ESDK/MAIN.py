# Copyright (c) 2021 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK Main board interface
'''

import smbus2
import toml
import threading
import re
import subprocess
import pkg_resources
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
    def __init__(self, config, debug=False):
        self.logger = AppLogger.getLogger(__name__, debug)
        try:
            self.bus = smbus2.SMBus(1)
        except Exception as e:
            raise e

        self.moduleNames = []
        self.sensorModules = {}
        self.sensorData = {}
        self.configDict = config
        self.location = {}
        self.gpsStatus = {"gpsStatus": {}}
        self._parseConfig()

    def _parseConfig(self):
        """ Parse config when mainboard initialised """

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
                        self.gpsStatus['gpsStatus'].update({'mode': result.get("mode", 0)})

                    if result["class"] == "SKY":
                        satellitesList = result.get("satellites", "")
                        satellitesUsedCount = 0

                        for satellite in satellitesList:
                            if satellite['used']:
                                satellitesUsedCount = satellitesUsedCount + 1

                        self.gpsStatus['gpsStatus'].update({'satellitesUsed': satellitesUsedCount})

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

    def getLocation(self):
        """ Return either actual GPS location, or config file location """
        if self.configDict['ESDK']['gps'] == False or self.configDict['ESDK']['gps'] is None:
            location['lat'] = self.configDict['ESDK']['latitude']
            location['lon'] = self.configDict['ESDK']['longitude']
            return location

        if self.configDict['ESDK']['gps'] == True:
            if "lat" and "lon" in self.location:
                return self.location
            else:
                return {}

    def getGPSStatus(self):
        """ Return GPS status """
        return self.gpsStatus

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

    def getModuleVersion(self):
        """ Return the ESDK module version """
        return {"moduleVersion": pkg_resources.get_distribution('DesignSpark.ESDK').version}

    def getUndervoltageStatus(self):
        """ Try to read the undervoltage status """
        try:
            cmdOutput = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True)
            statusData = cmdOutput.stdout.decode('ascii').strip().strip("throttled=")

            code = int(statusData, 16)
            status = {"code": code}
            response = {"throttle_state": status}

            if statusData == "0x0":
                return response

            statusBits = [[0, "Under_Voltage detected"],
                    [1, "Arm frequency capped"],
                    [2, "Currently throttled"],
                    [3, "Soft temperature limit active"],
                    [16, "Under-voltage has occurred"],
                    [17, "Arm frequency capping has occurred"],
                    [18, "Throttling has occurred"],
                    [19, "Soft temperature limit has occurred"]]

            statusStrings = []

            for x in range(0, len(status_bits)):
                statusBitString = statusBits[x][1]
                if (statusCode & (1 << statusBits)):
                    statusStrings.append(statusBitString)

            status.update({"status_strings": statusStrings})
            response = {"throttle_state": status}
            return response

        except Exception as e:
            self.logger.error("Could not retrieve undervoltage status, reason {}".format(e))
            return -1