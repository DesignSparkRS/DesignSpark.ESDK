# Copyright (c) 2022 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK NO2 board interface
'''

import time
import smbus2
from smbus2 import i2c_msg

moduleVersionString = "NO20.1"

ADC_ADDR = 0x40

ADC_REF = 3.000

ADC_UPPER = 0x7FFF

class ModNO2:
	""" This is a class that handles interfacing with the ESDK-PM2 board.

	:param sensitivity: Sensitivity code from barcode on sensor
	:type sensitivity: float
	:param tia_gain: Transimpedance amplifier gain from sensor datasheet
	:type tia_gain: float
	:param voffset: Offset voltage used in gas calculation
	:type voffset: float
	"""
	def __init__(self, sensitivity=-20.86, tia_gain=499, voffset=0):
		try:
			self.bus = smbus2.SMBus(1)

			# Sensitivity should be read from the back of the sensing element
			# As this varies from device to device
			self.sensitivity = sensitivity

			# TIA gain is provided by the Spec datasheet, and only changes on sensing element type
			self.tia_gain = tia_gain

			# Voffset figure used in calculation of gas concentration
			self.voffset = voffset

			# Constant used in calculation of gas concentration
			self.m = self.sensitivity * self.tia_gain * (10^-9) * (10^3)
		except Exception as e:
			raise e

		self._resetADC()

	def _resetADC(self):
		""" Issues reset command to ADC. """
		try:
			self.bus.write_byte(ADC_ADDR, 0x06)
		except Exception as e:
			raise e

	def _isDataReady(self):
		""" Queries ADC to see if data is available to be read.

		:return: True or false if ADC data is available.
		:rtype: bool

		"""
		try:
			write = i2c_msg.write(ADC_ADDR, [0x24])
			read = i2c_msg.read(ADC_ADDR, 1)
			self.bus.i2c_rdwr(write, read)

			ready = list(read)[0] >> 7

			if ready == 1:
				return True
			else:
				return False
		except Exception as e:
			raise e

	def _readVrefChannel(self):
		""" Read and convert AIN1 (sensor Vref) to a voltage. 

		:return: The voltage of AIN1 (sensor Vref).
		:rtype: float

		"""
		try:
			# 0x81 is the config register data
			# AINp = AIN1, AINn = GND
			# Gain = 1
			# 20 SPS
			# Single conversion
			# External reference
			self.bus.write_byte_data(ADC_ADDR, 0x40, 0x81)

			# Trigger read
			self.bus.write_byte(ADC_ADDR, 0x08)

			time.sleep(0.05)

			if self._isDataReady():
				write = i2c_msg.write(ADC_ADDR, [0x10])
				read = i2c_msg.read(ADC_ADDR, 2)
				self.bus.i2c_rdwr(write, read)

				read = list(read)
				voltage = ((read[0] << 8) + read[1]) * (ADC_REF / ADC_UPPER)
				return round(voltage, 3)
			else:
				return -1
		except Exception as e:
			raise e

	def _readVgasChannel(self):
		""" Read and convert AIN0 (sensor Vgas) to a voltage. 

		:return: The voltage of AIN0 (sensor Vgas).
		:rtype: float

		"""
		try:
			# 0x61 is the config register data
			# AINp = AIN0, AINn = GND
			# Gain = 1
			# 20 SPS
			# Single conversion
			# External reference
			self.bus.write_byte_data(ADC_ADDR, 0x40, 0x61)

			# Trigger read
			self.bus.write_byte(ADC_ADDR, 0x08)

			time.sleep(0.05)

			if self._isDataReady():
				write = i2c_msg.write(ADC_ADDR, [0x10])
				read = i2c_msg.read(ADC_ADDR, 2)
				self.bus.i2c_rdwr(write, read)

				read = list(read)
				voltage = ((read[0] << 8) + read[1]) * (ADC_REF / ADC_UPPER)
				return round(voltage, 3)
			else:
				return -1
		except Exception as e:
			raise e

	def _readVtempChannel(self):
		""" Read and convert AIN2 (sensor Vtemp) to a voltage.

		:return: The voltage of AIN2 (sensor Vtemp).
		:rtype: float
		
		"""
		try:
			# 0xA1 is the config register data
			# AINp = AIN2, AINn = GND
			# Gain = 1
			# 20 SPS
			# Single conversion
			# External reference
			self.bus.write_byte_data(ADC_ADDR, 0x40, 0xA1)

			# Trigger read
			self.bus.write_byte(ADC_ADDR, 0x08)

			time.sleep(0.05)

			if self._isDataReady():
				write = i2c_msg.write(ADC_ADDR, [0x10])
				read = i2c_msg.read(ADC_ADDR, 2)
				self.bus.i2c_rdwr(write, read)

				read = list(read)
				voltage = ((read[0] << 8) + read[1]) * (ADC_REF / ADC_UPPER)
				return round(voltage, 3)
			else:
				return -1
		except Exception as e:
			raise e

	def readNO2(self):
		""" Read ADC and calculate an NO2 reading. 

		:return: The NO2 concentration.
		:rtype: float

		"""
		vgas = self._readVgasChannel()
		vref = self._readVrefChannel()

		if vgas != -1 and vref != -1:
			vgas0 = vref + self.voffset

			conc = (1 / self.m) * (vgas - vgas0)

			return round(conc, 2)
		else:
			return -1

	def readSensors(self):
		""" Reads sensor and returns a dictionary containing module version, and all readings.

        :return: A dictionary containing

        .. code-block:: text
            
            {
                "no2":{
                    "sensor":"NO20.1",
                    "no2":2.1,
                }
            }
            
        Or -1 if data is unavailable

        :rtype: dict, int

        """
		try:
			sensorData = {}
			no2 = self.readNO2()
			sensorData['sensor'] = moduleVersionString
			if no2 != -1:
				sensorData['no2'] = no2
				return {'no2': sensorData}
			else:
				return -1
		except Exception as e:
			raise e