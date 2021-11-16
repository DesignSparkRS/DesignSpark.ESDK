# Copyright (c) 2021 RS Components Ltd
# SPDX-License-Identifier: MIT License

'''
Logging functions
'''

import logging

_format = "%(asctime)s [%(levelname)s] %(name)s %(threadName)s: %(message)s"

def getStreamHandler(debug):
    stream_handler = logging.StreamHandler()
    if debug:
        stream_handler.setLevel(logging.DEBUG)
    else:
        stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(_format))
    return stream_handler

def getLogger(name, debug=False):
    logger = logging.getLogger(name)
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.addHandler(getStreamHandler(debug))

    return logger