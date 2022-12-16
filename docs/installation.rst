Installation
------------

This guide assumes that you are running Raspberry Pi OS.

First enable I2C:

.. code-block:: console

    pi@raspberrypi:~$ sudo raspi-config

Selecting:

* Option 5 - Interfacing
* P5 - I2C
* Enable → YES

Then exit raspi-config.

Next update the system:

.. code-block:: console

    pi@raspberrypi:~$ sudo apt update && sudo apt dist-upgrade

Finally, install DesignSpark.ESDK and dependencies from PyPi:

.. code-block:: console

    pi@raspberrypi:~$ sudo pip install designspark.esdk
