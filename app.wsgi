#!/usr/bin/python3

import logging
import sys

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '<PATH TO THIS FOLDER>')

from app import app as application

application.secret_key = '<CHANGE ME>'
