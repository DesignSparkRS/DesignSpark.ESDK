# Copyright (c) 2021 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK PM2 board interface
'''

import time
import smbus2
from smbus2 import i2c_msg

moduleVersionString = "PM20.2"

SPS_ADDR = 0x69

class ModPM2:
    def __init__(self):
        try:
            self.bus = smbus2.SMBus(1)
        except Exception as e:
            raise e

        self.__reset()
        self.__wakeSensor()
        self.startMeasurement()

    def __calculateCrc(self, input):
        """ Calculate CRC for communicating with SPS30 """
        ''' Taken from https://github.com/DFRobot/DFRobot_SGP40/blob/master/Python/raspberrypi/DFRobot_SGP40.py '''
        crc = 0xff
        for i in range(0,2):
            crc = crc^input[i]
            for bit in range(0,8):
                if(crc&0x80):
                    crc = ((crc <<1)^0x31)
                else:
                    crc = (crc<<1)
            crc = crc&0xFF
        return crc

    def __isDataReady(self):
        """ Query SPS30 to see if there is available data to read """
        try:
            write = i2c_msg.write(SPS_ADDR, [0x02, 0x02])
            read = i2c_msg.read(SPS_ADDR, 3)
            self.bus.i2c_rdwr(write)
            time.sleep(0.001)
            self.bus.i2c_rdwr(read)
            if list(read)[1] == 0x01:
                return True
            else:
                return False
        except Exception as e:
            raise e

    def __reset(self):
        """ Attempt to reset sensor and delay for the reset time period """
        try:
            self.bus.write_i2c_block_data(SPS_ADDR, 0xD3, [0x04])
            time.sleep(0.1)
        except Exception as e:
            raise e

    def __wakeSensor(self):
        """ Send command to wake sensor twice, as per SPS30 datasheet """
        try:
            self.bus.write_i2c_block_data(SPS_ADDR, 0x11, [0x03])
            self.bus.write_i2c_block_data(SPS_ADDR, 0x11, [0x03])
        except Exception as e:
            raise e

    def startMeasurement(self):
        """ Starts measurement with returned values being u16 integers """
        try:
            command = [0x00, 0x10, 0x05, 0x00]
            crc = self.__calculateCrc(command[2:4])
            command.append(crc)
            write = i2c_msg.write(SPS_ADDR, command)
            self.bus.i2c_rdwr(write)
        except Exception as e:
            raise e

    def __readSensor(self):
        """ Attempt to read sensor data and parse into dictionary of PM values """
        try:
            write = i2c_msg.write(SPS_ADDR, [0x03, 0x00])
            read = i2c_msg.read(SPS_ADDR, 30)
            self.bus.i2c_rdwr(write)
            time.sleep(0.001)
            self.bus.i2c_rdwr(read)
            raw_data = list(read)

            # Convert to integer values
            pm10 = (raw_data[0] << 8) + raw_data[1]
            pm25 = (raw_data[3] << 8) + raw_data[4]
            pm40 = (raw_data[6] << 8) + raw_data[7]
            pm100 = (raw_data[9] << 8) + raw_data[10]

            data = {
                "pm1.0": pm10,
                "pm2.5": pm25,
                "pm4.0": pm40,
                "pm10": pm100
            }

            return data
        except Exception as e:
            raise e

    def readSensors(self):
        """ Attempt to read sensor values """
        try:
            if self.__isDataReady():
                sensorData = {"sensor": moduleVersionString}
                sensorData.update(self.__readSensor())
                return {'pm': sensorData}
            else:
                return -1
        except Exception as e:
            raise e

    def startFanCleaning(self):
        """ Start fan cleaning procedure """
        try:
            self.bus.write_i2c_block_data(SPS_ADDR, 0x56, [0x07])
        except Exception as e:
            raise e