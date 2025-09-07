from Core.core import Core
import socket as sc
import logging

logging.basicConfig(level=logging.DEBUG)

vyrn = Core(host="localhost", port=8080)
vyrn.start()