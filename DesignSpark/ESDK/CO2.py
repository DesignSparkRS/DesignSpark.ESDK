# Copyright (c) 2021 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK CO2 board interface
'''

import time
import smbus2
from smbus2 import i2c_msg

moduleVersionString = "CO20.2"

SCD_ADDR = 0x62

class ModCO2:
    """ This is a class that handles interfacing with the ESDK-CO2 board. """
    def __init__(self):
        try:
            self.bus = smbus2.SMBus(1)
        except Exception as e:
            raise e

        self.__startPeriodicMeasurement()

    def __startPeriodicMeasurement(self):
        """ Starts periodic measurement mode. """
        try:
            self.bus.write_i2c_block_data(SCD_ADDR, 0x21, [0xB1])
        except Exception as e:
            raise e

    def __isDataReady(self):
        """ Query SCD4x to see if there is available readings

        :return: A boolean value indicating if there is a reading available
        :rtype: bool

        """
        try:
            write = i2c_msg.write(SCD_ADDR, [0xE4, 0xB8])
            read = i2c_msg.read(SCD_ADDR, 3)
            self.bus.i2c_rdwr(write, read)
            state = (list(read)[0] << 8) + list(read)[1]
            if state != 0x8000:
                return True
            else:
                return False
        except Exception as e:
            raise e

    def __readSensorData(self):
        """ Reads all available sensor data

        :return: A list of 9 bytes from the sensor
        :rtype: list

        """
        try:
            write = i2c_msg.write(SCD_ADDR, [0xEC, 0x05])
            read = i2c_msg.read(SCD_ADDR, 9)
            self.bus.i2c_rdwr(write, read)
            return list(read)
        except Exception as e:
            raise e

    def readCO2(self):
        """ Reads a CO2 value from the sensor

        :return: A CO2 reading in ppm, or -1 if the sensor is not ready
        :rtype: int

        """
        try:
            if self.__isDataReady():
                v = self.__readSensorData()
                co2 = (v[0] << 8) + v[1]

                return co2
            else:
                return -1
        except Exception as e:
            raise e

    def readTempAndHumidity(self):
        """ Reads temperature and humidity from the sensor

        :return: A dictionary containing:

        .. code-block:: text

            {
                "temp":12.3,
                "humidity":50.3
            }

        Or -1 if sensor data is unavailable

        :rtype: dict, int
        """
        try:
            if self.__isDataReady():
                v = self.__readSensorData()
                
                temperature = round(-45 + (175 * ((v[3] << 8) + v[4]) / 65535.0), 1)
                humidity = round(100 * ((v[6] << 8) + v[7]) / 65535.0, 1)

                rv = {
                "temp": temperature,
                "humidity": humidity
                }

                return rv
            else:
                return -1
        except Exception as e:
            raise e

    def readSensors(self):
        """ Reads sensors and returns a dictionary containing module version, and all readings.

        :return: A dictionary containing

        .. code-block:: text
            
            {
                "co2":{
                    "sensor":"CO20.2",
                    "co2":453
                }
            }
            
        Or -1 if data is unavailable

        :rtype: dict, int

        """
        try:
            sensorData = {}
            co2Reading = self.readCO2()
            sensorData['sensor'] = moduleVersionString
            if co2Reading != -1:
                sensorData['co2'] = co2Reading
                return {'co2': sensorData}
            else:
                return -1
        except Exception as e:
            raise e