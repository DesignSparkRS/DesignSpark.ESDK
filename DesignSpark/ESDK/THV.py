# Copyright (c) 2021 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK THV board interface
'''

import smbus2
from smbus2 import i2c_msg
import time
from .DFRobot_SGP40_VOCAlgorithm import DFRobot_VOCAlgorithm

moduleVersionString = "THV0.2"

SHT_ADDR = 0x44
SGP_ADDR = 0x59

# SGP40 commands
SGP40_MEASURE_RAW_SIGNAL = [0x26, 0x0F]
SGP40_EXECUTE_SELF_TEST = [0x28, 0x0E]
SGP40_TURN_HEATER_OFF = [0x36, 0x15]
SGP4X_GET_SERIAL_NUMBER = [0x36, 0x82]
SGP40_MEASURE_RAW_NO_COMP = [0x26, 0x0F, 0x80, 0x00, 0xA2, 0x66, 0x66, 0x93]


class ModTHV:
    """ This is a class that handles interfacing with the ESDK-THV board. """
    def __init__(self):
        self.algorithm = DFRobot_VOCAlgorithm()
        self.algorithm.vocalgorithm_init()

        try:
            self.bus = smbus2.SMBus(1)
        except Exception as e:
            raise e
        
        startTime = int(time.time())
        while (int(time.time()) - startTime < 10):
            self.readVocIndex()

    def __sgp40_crc(self, data1, data2):
        """ Calculates a CRC for two bytes of data, according to SGP40 datasheet. """
        ''' Taken from https://github.com/DFRobot/DFRobot_SGP40/blob/master/Python/raspberrypi/DFRobot_SGP40.py '''
        crc = 0xff
        list = [data1, data2]
        for i in range(0,2):
            crc = crc^list[i]
            for bit in range(0,8):
                if(crc&0x80):
                    crc = ((crc <<1)^0x31)
                else:
                    crc = (crc<<1)
            crc = crc&0xFF
        return crc

    def __readTempAndHumidityRaw(self):
        """ Queries SHT31 and returns a dictionary of raw temperature and humidity values.

        :return: A dictionary containing

        .. code-block:: text
            
            {
                "temp":1234,
                "humidity":5678
            }

        :rtype: dict

        """
        try:
            ''' Send high repeatability measurement command without clock stretching '''
            self.bus.write_i2c_block_data(SHT_ADDR, 0x24, [0x00])

            time.sleep(0.5)

            raw_data = self.bus.read_i2c_block_data(SHT_ADDR, 0x00, 6)
            raw_temp = raw_data[0] * 256 + raw_data[1]
            raw_humidity = raw_data[3] * 256 + raw_data[4]

            values = {
                "temp": raw_temp,
                "humidity": raw_humidity
            }

            return values
        except Exception as e:
            raise e

    def readTempAndHumidity(self):
        """ Queries SHT31 and returns a dictionary of temperature and humidity values.

        :return: A dictionary containing

        .. code-block:: text
            
            {
                "temperature":12.3,
                "humidity":50.3
            }

        :rtype: dict

        """
        try:
            v = self.__readTempAndHumidityRaw()

            ''' Calculations taken from SHT31 datasheet, section 4.13 '''
            temperature = round(-45 + (175 * v['temp'] / 65535.0), 1)
            humidity = round(100 * v['humidity'] / 65535.0, 1)

            values = {
                "temperature": temperature,
                "humidity": humidity
            }

            return values
        except Exception as e:
            raise e

    def readVocRaw(self):
        """ Returns a compensated raw VOC value. 

        :return: An integer VOC value
        :rtype: int
        """
        try:
            th = self.__readTempAndHumidityRaw()
            ''' Split values into upper and lower bytes to prepare for sending to sensor '''
            tempUpperByte = int(th['temp']) >> 8
            tempLowerByte = int(th['temp']) & 0xFF

            humidityUpperByte = int(th['humidity']) >> 8
            humidityLowerByte = int(th['humidity']) & 0xFF

            tempCrc = self.__sgp40_crc(tempUpperByte, tempLowerByte)
            humidityCrc = self.__sgp40_crc(humidityUpperByte, humidityLowerByte)

            ''' Perform write and then read after 30ms delay, as per datasheet '''
            write = i2c_msg.write(SGP_ADDR, [0x26, 0x0F, humidityUpperByte, humidityLowerByte, humidityCrc, tempUpperByte, tempLowerByte, tempCrc])
            read = i2c_msg.read(SGP_ADDR, 3)
            self.bus.i2c_rdwr(write)
            time.sleep(0.03)
            self.bus.i2c_rdwr(read)
            read = list(read)

            if self.__sgp40_crc(read[0], read[1]) == read[2]:
                vocRaw = (read[0] << 8) + read[1]
                return vocRaw
            else:
                return -1
        except Exception as e:
            raise e

    def readVocIndex(self):
        """ Returns a calculated VOC index value.

        :return: An integer VOC index value, or -1 if unavailable
        :rtype: int
        """
        vocRaw = self.readVocRaw()

        if vocRaw < 0:
            return -1
        else:
            vocIndex = self.algorithm.vocalgorithm_process(vocRaw)
            return vocIndex

    def readSensors(self):
        """ Reads sensors and returns a dictionary containing module version, and all readings.

        :return: A dictionary containing

        .. code-block:: text
            
            {
                "thv":{
                    "sensor":"THV0.2",
                    "temperature":21.2,
                    "humidity":50.3,
                    "vocIndex":100
                }
            }
            
        Or -1 if data is unavailable

        :rtype: dict, int

        """
        try:
            sensorData = {}
            vocIndex = self.readVocIndex()
            tempAndHumidity = self.readTempAndHumidity()
            if vocIndex != -1 and tempAndHumidity != -1:
                sensorData['vocIndex'] = vocIndex
                sensorData.update(tempAndHumidity)
                sensorData['sensor'] = moduleVersionString
                return {"thv": sensorData}
            else:
                return -1
        except Exception as e:
            raise e