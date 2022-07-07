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
import imp
import inspect
import os
import RPi.GPIO as GPIO
from gpsdclient import GPSDClient
from . import AppLogger
from . import MAIN, THV, CO2, PM2, NO2, NRD, FDH

possibleModules = {
    "THV": 0x44, 
    "CO2": 0x62, 
    "PM2": 0x69,
    "NO2": 0x40,
    "NRD": 0x60,
    "FDH": 0x5D
}

moduleTypeDict = {
    'THV': THV,
    'CO2': CO2,
    'PM2': PM2,
    'NO2': NO2,
    "NRD": NRD,
    "FDH": FDH
}

# GPIOs used for board features
SENSOR_3V3_EN = 7
SENSOR_5V_EN = 16
BUZZER_PIN = 26
GPIO_LIST = [SENSOR_3V3_EN, SENSOR_5V_EN, BUZZER_PIN]

strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")

class ModMAIN:
    """ This class handles the ESDK mainboard, and it's various features.

    :param config: A dictionary containing configuration data with a minimum of:

    .. code-block:: text

        {
            "esdk":{
                "GPS":False
            }
        }
    
    :type config: dict
    :param debug: Debug logging control, defaults to False
    :type debug: bool, optional
    :param loggingLevel: One of 'off', 'error' or 'full' to control file logging, defaults to 'full'
    :type loggingLevel: str, optional
    :param pluginDir: A string value containing a file path to a plugin directory, defaults to None
    :type pluginDir: str, optional
    """
    def __init__(self, config, debug=False, loggingLevel='full', pluginDir=None):
        self.logger = AppLogger.getLogger(__name__, debug, loggingLevel)
        try:
            self.bus = smbus2.SMBus(1)

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(GPIO_LIST, GPIO.OUT)
            self.buzzer_pwm = GPIO.PWM(BUZZER_PIN, 1000)
        except Exception as e:
            raise e

        self.moduleNames = []
        self.sensorModules = {}
        self.sensorData = {}
        self.configDict = config
        self.location = {}
        self.gpsStatus = {"gpsStatus": {}}
        self.pluginDir = pluginDir
        self.pluginsModuleList = []
        self.plugins = []
        self._parseConfig()

    def _parseConfig(self):
        """ Parse config when mainboard initialised """
        if 'ESDK' in self.configDict:
            if 'gps' in self.configDict['ESDK']:
                if self.configDict['ESDK']['gps'] is not None:
                    if self.configDict['ESDK']['gps'] == True:
                        self.logger.info("GPS is enabled")
                        self.gps = GPSDClient(host="localhost")
                        gpsHandlerThreadHandle = threading.Thread(target=self._gpsHandlerThread, daemon=True)
                        gpsHandlerThreadHandle.name = "gpsHandlerThread"
                        gpsHandlerThreadHandle.start()

    def _gpsHandlerThread(self):
        """ Thread for polling GPS module. """
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
        """ Probes I2C bus to attempt to find sensor modules. """
        self.moduleNames.clear()
        self.logger.debug("Starting module probe")
        for module, addr in possibleModules.items():
            try:
                # ADC used on NO2 board is an annoying edge case, does not seemingly acknowledge 0x0
                if module != "NO2":
                    self.bus.write_byte(addr, 0)
                    self.moduleNames.append(module)
                else:
                    # Instead issue reset command, and check for an acknowledgement
                    self.bus.write_byte(addr, 0x06)
                    self.moduleNames.append(module)
            except Exception as e:
                # Ignore any that fail - the modules aren't present on the bus
                pass
        self.logger.info("Found modules {}".format(self.moduleNames))

    def getLocation(self):
        """ Returns a dictionary containing GPS location, or configuration file location if GPS is disabled.

        :return: A dictionary containing:

        .. code-block:: text

            {
                "lat":0.0,
                "lon":0.0
            }

        :rtype: dict

        """
        if self.configDict['ESDK']['gps'] == False or self.configDict['ESDK']['gps'] is None:
            self.location['lat'] = self.configDict['ESDK']['latitude']
            self.location['lon'] = self.configDict['ESDK']['longitude']
            return self.location

        if self.configDict['ESDK']['gps'] == True:
            if "lat" and "lon" in self.location:
                return self.location
            else:
                return {}

    def getGPSStatus(self):
        """ Returns a dictionary containing GPS status. 

        :return: A dictionary containing:

        .. code-block:: text

            {
                "gpsStatus":{
                    "mode":0,
                    "satellites":13,
                    "satellitesUsed":5
                }
            }

        :rtype: dict

        """
        return self.gpsStatus

    def createModules(self):
        """ Discovers and instantiates module objects for use with ``readAllModules()``. """
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

                if moduleName == "NO2":
                    self.sensorModules[moduleName] = moduleTypeDict[moduleName].ModNO2()

                if moduleName == "NRD":
                    self.sensorModules[moduleName] = moduleTypeDict[moduleName].ModNRD()

                if moduleName == "FDH":
                    self.sensorModules[moduleName] = moduleTypeDict[moduleName].ModFDH()
            except Exception as e:
                self.logger.error("Could not create module {}, reason {}".format(moduleName, e))

    def readAllModules(self):
        """ Reads all sensor modules and returns a dictionary containing sensor data. """
        try:
            for name, module in self.sensorModules.items():
                self.logger.debug("Trying to read sensor {}".format(name))
                data = module.readSensors()
                if data != -1:
                    self.sensorData.update(data)
        except Exception as e:
            self.logger.error("Could not read module {}, reason {}".format(name, e))

        # Read loaded plugins
        try:
            for plugin in self.plugins:
                pluginName = plugin.__class__.__name__
                self.logger.debug("Trying to read plugin {}".format(pluginName))
                try:
                    data = plugin.readSensors()
                    if data != -1:
                        self.sensorData.update(data)
                except Exception as e:
                    self.logger.error("Could not read plugin {}, reason {}".format(pluginName, e))
        except Exception as e:
            self.logger.error("Error handling plugins, reason {}".format(e))

        self.logger.debug("Sensor data {}".format(self.sensorData))
        return self.sensorData

    def getSerialNumber(self):
        """ Returns a dictionary containing the Raspberry Pi serial number.

        :return: A dictionary containing:

        .. code-block:: text

            {
                "serialNumber":"RPI0123456789"
            }

        :rtype: dict

        """
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
        """ Returns a dictionary containing ESDK module version.

        :return: A dictionary containing:

        .. code-block:: text

            {
                "moduleVerson":"0.0.1"
            }

        :rtype: dict

        """
        return {"moduleVersion": pkg_resources.get_distribution('DesignSpark.ESDK').version}

    def getUndervoltageStatus(self):
        """ Returns a dictionary containing the Raspberry Pi throttle status and code.

        :return: A dictionary containing (throttle_state is optional, and only populated should a nonzero code exist)

        .. code-block:: text

            {
                "throttle_state":{
                    "code":0,
                    "throttle_state":""
                }
            }

        :rtype: dict

        """
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

            for x in range(0, len(statusBits)):
                statusBitString = statusBits[x][1]
                if (code & (1 << statusBits[x][0])):
                    statusStrings.append(statusBitString)

            status.update({"status_strings": statusStrings})
            response = {"throttle_state": status}
            return response

        except Exception as e:
            self.logger.error("Could not retrieve undervoltage status, reason {}".format(e))
            return -1

    def setPower(self, vcc3=False, vcc5=False):
        """ Switches 3.3V and 5V sensor power supply rails according to supplied arguments.

        :param vcc3: 3.3V sensor power supply status, defaults to False
        :type vcc3: bool, optional
        :param vcc5: 5V sensor power supply status, defaults to False
        :type vcc5: bool, optional
        """
        try:
            self.logger.debug("Setting sensor power rails, 3V3: {}, 5V: {}".format(vcc3, vcc5))
            GPIO.output(SENSOR_3V3_EN, vcc3)
            GPIO.output(SENSOR_5V_EN, vcc5)
        except Exception as e:
            raise e

    def setBuzzer(self, freq=0):
        """ Sets a PWM frequency on the buzzer output.

        :param freq: Buzzer frequency, 0 stops the buzzer
        :type freq: int, optional
        """
        try:
            if freq > 0:
                self.logger.debug("Setting buzzer frequency to {}".format(freq))
                self.buzzer_pwm.start(50)
                self.buzzer_pwm.ChangeFrequency(freq)

            if freq == 0:
                self.logger.debug("Stopping buzzer")
                self.buzzer_pwm.stop()
        except Exception as e:
            raise e

    def loadPlugins(self):
        """ Attempts to load and instantiate plugins from a specified folder. """
        if self.pluginDir == None:
            cwd = os.getcwd()
            self.pluginFullPath = cwd + "/plugins"
            self.logger.debug("No plugin folder provided, using default")
            self.logger.debug("Current working directory: {}, plugins path: {}".format(cwd, self.pluginFullPath))
        else:
            self.pluginFullPath = self.pluginDir

        # Create a list of available plugin modules
        for filename in os.listdir(self.pluginFullPath):
            modulename, extension = os.path.splitext(filename)
            if extension == '.py':
                file, path, descr = imp.find_module(modulename, [self.pluginFullPath])
                if file:
                    try:
                        self.logger.debug("Found plugin module: {}".format(file.name))
                        module = imp.load_module(modulename, file, path, descr)
                        self.pluginsModuleList.append(module)
                    except Exception as e:
                        self.logger.error("Could not load plugin {}! Reason {}".format(file.name, e))

        # Create a list of instantiated plugin classes
        for pluginModule in self.pluginsModuleList:
            for name, obj in inspect.getmembers(pluginModule):
                if inspect.isclass(obj):
                    self.logger.debug("Created plugin class {}".format(obj))
                    self.plugins.append(obj())

        self.logger.info("Loaded {} plugin(s)".format(len(self.plugins)))
