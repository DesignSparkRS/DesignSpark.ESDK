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
    def __init__(self):
        try:
            self.bus = smbus2.SMBus(1)
        except Exception as e:
            raise e

        self.__startPeriodicMeasurement()

    def __startPeriodicMeasurement(self):
        """ Start periodic measurement mode, period of 5s between updated values """
        try:
            self.bus.write_i2c_block_data(SCD_ADDR, 0x21, [0xB1])
        except Exception as e:
            raise e

    def __isDataReady(self):
        """ Query SCD4x to see if there is available readings """
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
        """ Read all available sensor data """
        try:
            write = i2c_msg.write(SCD_ADDR, [0xEC, 0x05])
            read = i2c_msg.read(SCD_ADDR, 9)
            self.bus.i2c_rdwr(write, read)
            return list(read)
        except Exception as e:
            raise e

    def readCO2(self):
        """ Read CO2 data from sensor if available """
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
        """ Read temperature and humidity from sensor if available """
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