# Copyright (c) 2022 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK FDH board interface
'''

import time
import smbus2
from smbus2 import i2c_msg

moduleVersionString = "FDH0.1"

SFA_ADDR = 0x5D

class ModFDH:
	""" This is a class that handles interfacing with the ESDK-FDH board. """
	def _init__(self):
		try:
			self.bus = smbus2.SMBus(1)
		except Exception as e:
			raise e

	def _startPeriodicMeasurement(self):
		""" Starts the sensor periodic measurement mode. """
		try:
			self.bus.write_i2c_block_data(SFA_ADDR, 0x00, [0x06])
		except Exception as e:
			raise e

	def _readSensorData(self):
		""" Reads all available sensor data

		:return: A list of 9 bytes of sensor data
		:rtype: list

		"""

		try:
			write = i2c_msg.write(SFA_ADDR, [0x03, 0x27])
			read = i2c_msg.read(SFA_ADDR, 9)
			return list(read)
		except Exception as e:
			raise e

	def readFormaldehyde(self):
		""" Reads a formaldehyde value from the sensor

		:return: A HCHO reading in ppb
		:rtype: int

		"""
		try:
			data = self._readSensorData()
			hcho = int(((data[0] << 8) + data[1]) / 5.0)
			return hcho
		except Exception as e:
			raise e

	def readSensors(self):
		""" Reads sensors and returns a dictionary containing module version and readings.

		:return: A dictionary containing

		.. code-block:: text

			{
				"fdh":{
					"sensor":"FDH0.1",
					"formaldehyde":25
				}
			}

		:rtype: dict

		"""
		try:
			sensorData = {}
			hcho = self.readFormaldehyde()
			sensorData['sensor'] = moduleVersionString
			sensorData['formaldehyde'] = hcho
			return {'fdh': sensorData}
		except Exception as e:
			raise e