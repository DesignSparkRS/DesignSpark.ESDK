Writing Plugins
===============

**Plugins are currently an experimental feature, and only support for reading sensors has been implemented.**

A plugin is a Python module that expands the ESDK ecosystem to support additional sensors.

Requirements
------------

At the bare minimum, a plugin contains a class with a function called ``readSensors`` that returns a dictionary containing the sensor data. Should no data be available, a value of -1 should be returned in place of the dictionary.

The sensor data dictionary **should** contain certain data::

	{
		"sensorname": {
			"sensor": "sensorversion"
		}
	}

The ``sensorname`` key should be a descriptive, short name for the sensor. For example, the ESDK sensor boards are ``thv``, ``co2`` and ``pm2``. 

The ``sensorversion`` value should be a string containing a revision of the sensor board or plugin module. For example, the ESDK sensor boards are ``THV0.2``, ``CO20.2`` and ``PM20.2`` (board name plus a hardware version number).

Sensor data can be inserted into the innermost object, alongside the ``sensor`` key. For example, the sensor data structure for a PIR sensor plugged into the ESDK-EEA board would look like the following::

	{
		"pir": {
			"motion": "1",
			"sensor": "pirplugin0.1"
		}
	}

Example
-------

A simple example that reads a GPIO pin is provided below::

	import RPi.GPIO as GPIO
	GPIO1 = 20

	class PIR:
        def __init__(self):
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(GPIO1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        def readSensors(self):
                pirState = GPIO.input(GPIO1)
                return {"pir": {"motion": str(pirState), "sensor": "pirplugin0.1"}}


Usage
-----

By default, ``ModMAIN`` looks for a ``plugins`` directory in the current working directory of the Python script that has instantiated the class, but this can be overridden by providing the ``pluginDir`` argument when instantiating the class. ::

	mb = MAIN.ModMAIN(config=config, debug=True, loggingLevel='off', pluginDir="/home/pi/plugins")

Plugins are loaded using the ``loadPlugins`` function, which attempts to import each module found in the specified directory.

Calling the function ``readAllModules`` attempts to read all the default sensor modules (i.e. THV, CO2 and PM2), and then attempts to read the plugin sensors. The function then returns a dictionary containing all the available sensor data.

Exceptions
----------

Exceptions are handled internally within the ModMAIN class, and errors are logged where necessary. If a plugin isn't working, check for errors in the logs to pinpoint where the issue lies.