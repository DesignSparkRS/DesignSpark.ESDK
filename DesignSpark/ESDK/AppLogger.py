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

def getLogFileHandler(debug, logFile='/aq/log/aq.log'):
    file_handler_log = logging.FileHandler(logFile, mode='w', encoding='utf-8')
    if debug:
        file_handler_log.setLevel(logging.DEBUG)
    else:
        file_handler_log.setLevel(logging.INFO)
    file_handler_log.setFormatter(logging.Formatter(_format))
    return file_handler_log

def getErrorLogFileHandler(errorFile='/aq/log/error.log'):
    file_handler_error = logging.FileHandler(errorFile, mode='w', encoding='utf-8')
    file_handler_error.setLevel(logging.ERROR)
    file_handler_error.setFormatter(logging.Formatter(_format))
    return file_handler_error

def getLogger(name, debug=False, loggingSetup='full'):
    logger = logging.getLogger(name)
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.addHandler(getStreamHandler(debug))

    if loggingSetup == 'full':
        logger.debug("Setting file logging to full")
        logger.addHandler(getLogFileHandler(debug))
        logger.addHandler(getErrorLogFileHandler())
    elif loggingSetup == 'error':
        logger.debug("Setting file logging to error only")
        logger.addHandler(getErrorLogFileHandler())
    elif loggingSetup == 'off':
        logger.debug("Setting file logging off")
    else:
        logger.warn("Invalid file logging level: {}".format(loggingSetup))

    return logger