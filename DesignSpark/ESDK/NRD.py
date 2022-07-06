# Copyright (c) 2022 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK NRD board interface
'''

import time
import smbus2
from smbus2 import i2c_msg

moduleVersionString = "NRD0.1"

MOD_ADDR = 0x60

class ModNRD:
	""" This is a class that handles interfacing with the ESDK-NRD board. """
	def __init__(self):
		try:
			self.bus = smbus2.SMBus(1)
		except Exception as e:
			raise e

	def enableI2CWatchdog(self):
		""" Enable NRD I2C watchdog functionality. """
		try:
			self.bus.write_i2c_block_data(MOD_ADDR, 0x07, [0x01])
		except Exception as e:
			raise e

	def disableI2CWatchdog(self):
		""" Disable NRD I2C watchdog functionality. """
		try:
			self.bus.write_i2c_block_data(MOD_ADDR, 0x07, [0x00])
		except Exception as e:
			raise e

	def enableEventLed(self):
		""" Enable the event detection LED. """
		try:
			self.bus.write_i2c_block_data(MOD_ADDR, 0x04, [0x01])
		except Exception as e:
			raise e

	def disableEventLed(self):
		""" Disable the event detection LED. """
		try:
			self.bus.write_i2c_block_data(MOD_ADDR, 0x04, [0x00])
		except Exception as e:
			raise e

	def enableEventGpio(self):
		""" Enable the event detection GPIO output. """
		try:
			self.bus.write_i2c_block_data(MOD_ADDR, 0x06, [0x01])
		except Exception as e:
			raise e

	def disableEventGpio(self):
		""" Disable the event detection GPIO output. """
		try:
			self.bus.write_i2c_block_data(MOD_ADDR, 0x06, [0x00])
		except Exception as e:
			raise e

	def getEventLedEnabledState(self):
		""" Get the event LED enabled state.

		:return: A boolean value indicating the event LED enabled status
		:rtype: bool

		"""
		try:
			status = self.bus.read_byte_data(MOD_ADDR, 0x04)
			if status == 0x01:
				return True
			if status == 0x00:
				return False
		except Exception as e:
			raise e

	def getEventGpioEnabledState(self):
		""" Get the event GPIO enabled state.

		:return: A boolean value indicating the event GPIO enabled status
		:rtype: bool

		"""
		try:
			status = self.bus.read_byte_data(MOD_ADDR, 0x06)
			if status == 0x01:
				return True
			if status == 0x00:
				return False
		except Exception as e:
			raise e

	def getI2CWatchdogEnabledState(self):
		""" Get the NRD I2C watchdog enabled state.

		:return: A boolean value indicating the watchdog enabled status
		:rtype: bool

		"""
		try:
			status = self.bus.read_byte_data(MOD_ADDR, 0x07)
			if status == 0x01:
				return True
			if status == 0x00:
				return False
		except Exception as e:
			raise e

	def readCountsPerSecond(self):
		""" Get the current CPS rate.

		:return: An integer representing counts-per-second
		:rtype: int

		"""

		try:
			cps = self.bus.read_byte_data(MOD_ADDR, 0x01)
			return cps
		except Exception as e:
			raise e

	def readCountsPerMinute(self):
		""" Get the current CPM rate.

		:return: An integer representing counts-per-minute
		:rtype: int

		"""

		try:
			write = i2c_msg.write(MOD_ADDR, [0x02])
			read = i2c_msg.read(MOD_ADDR, 2)
			self.bus.i2c_rdwr(write, read)
			data = list(read)

			cpm = int.from_bytes(data, "big")
			return cpm
		except Exception as e:
			raise e

	def readTotalCounts(self):
		""" Get the total accumulated event count

		:return: An integer representing accumulated event counts
		:rtype: int

		"""

		try:
			write = i2c_msg.write(MOD_ADDR, [0x03])
			read = i2c_msg.read(MOD_ADDR, 4)
			self.bus.i2c_rdwr(write, read)
			data = list(read)

			count = int.from_bytes(data, "big")
			return count
		except Exception as e:
			raise e

	def resetCounts(self):
		""" Reset all event counters. """
		try:
			self.bus.write_byte_data(MOD_ADDR, 0x05, 0x01)
		except Exception as e:
			raise e

	def readSensors(self):
		""" Reads sensors and returns a dictionary containing module version and readings.

		:return: A dictionary containing

		.. code-block:: text

			{
				"nrd":{
					"sensor":"NRD0.1",
					"cps":23,
					"cpm":483,
					"totalCounts":9465
				}
			}

		:rtype: dict

		"""

		try:
			sensorData = {}
			cpsReading = self.readCountsPerSecond()
			cpmReading = self.readCountsPerMinute()
			totalReading = self.readTotalCounts()

			sensorData['sensor'] = moduleVersionString
			sensorData['cps'] = cpsReading
			sensorData['cpm'] = cpmReading
			sensorData['totalCounts'] = totalReading

			return {'nrd': sensorData}
		except Exception as e:
			raise e