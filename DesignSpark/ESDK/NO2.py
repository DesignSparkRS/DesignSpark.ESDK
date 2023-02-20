# Copyright (c) 2022 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
ESDK NO2 board interface
'''

import time
import smbus2
import threading
import math
from smbus2 import i2c_msg
from statistics import mode

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
	:param movingAverageWindow: Window size for the NO2 moving average
	:type movingAverageWindow: int
	"""
	def __init__(self, sensitivity=-20.86, tia_gain=499, voffset=0, movingAverageWindow=15):
		try:
			self.bus = smbus2.SMBus(1)

			# Sensitivity should be read from the back of the sensing element
			# As this varies from device to device
			self.sensitivity = sensitivity

			# TIA gain is provided by the Spec datasheet, and only changes on sensing element type
			self.tia_gain = tia_gain

			# Voffset figure used in calculation of gas concentration
			self.voffset = voffset

			self.movingAverageWindow = movingAverageWindow

			self.no2AverageList = []
			# NO2 value updated in thread
			self.no2Value = 0
		except Exception as e:
			raise e

		self._resetADC()
		adcPollingThreadHandle = threading.Thread(target=self._adcPollingThread, daemon=True)
		adcPollingThreadHandle.name = "no2_adcPollingThreadHandle"
		adcPollingThreadHandle.start()

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

	def _calculateMovingAverage(self, new_data_point, data_list, average_size):
		""" Function to calculate a simple moving average """
		# Add fresh data
		data_list.insert(0, new_data_point)
		try:
			# Remove nth item in list
			data_list.pop(average_size)
		except Exception as e:
			pass
		total = 0
		total = sum(data_list)
        
		#value = math.ceil(total / len(data_list))
		value = round(total / len(data_list), 2)
		if(value == None):
			return 0
		else:
			return value

	def _adcPollingThread(self):
		""" Thread that polls the ADC to provid an updated NO2 value every five seconds """
		vref = -1
		vgasList = []
		vgasLastMode = 0

		while vref == -1:
			vref = self._readVrefChannel()

		while True:
			try:
				# Take 10 voltage readings from ADC
				for i in range(1, 10):
					vgas = -1
					# Wait until ADC says data is available
					while vgas == -1:
						vgas = self._readVgasChannel()
						time.sleep(0.1)

					# Append each sample to list and wait before taking another reading
					vgasList.append(vgas)
					time.sleep(0.25)
				# Take mode value for use in calculations to help reduce sensor noise (ADC and inputs seem noisy)
				try:
					vgasLastMode = vgas
					vgas = mode(vgasList)
				except Exception as e:
					vgasList.clear()

				if vgas != -1 and vref != -1:
					vgas0 = vref + self.voffset
					conc = (vgas - vgas0) / (self.tia_gain * 1e3) / (self.sensitivity * 1e-9)
					conc = round(conc, 2)
			except Exception as e:
				pass

			# Calculate moving average to use for value
			self.no2Value = self._calculateMovingAverage(conc, self.no2AverageList, self.movingAverageWindow)

			vgasList.clear()
			time.sleep(2.5)

	def readNO2(self):
		""" Returns an NO2 reading. 

		:return: The NO2 concentration.
		:rtype: float

		"""

		return self.no2Value

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