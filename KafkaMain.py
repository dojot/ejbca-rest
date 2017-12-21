# alternatively to the REST API
# one can use Kafka messages to configure ejbca-rest
# This file is the EJBCA kafka entry point
# the purpose of functions here is to verify input and pass
# the requests to the controller class
import logging
import kafka
import json
from time import sleep
import requests
from threading import Thread

import conf
from controller.RequestError import RequestError
import controller.UserController as uc
from ejbcaUtils import initicalConf

LOGGER = logging.getLogger('ejbca.' + __name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.DEBUG)


class KafkaConsumer(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        while True:
            LOGGER.debug("waiting for new messages")

            # To consume latest messages and auto-commit offsets
            while True:
                try:
                    consumer = (kafka.
                                KafkaConsumer('notifyDeviceChange',
                                              group_id='ejbca',
                                              bootstrap_servers=[conf.kafkaHost]
                                              ))
                    break
                except kafka.errors.NoBrokersAvailable:
                    LOGGER.error('Could not connect to Kafka at %s.'
                                 ' Chances are the server is not ready yet.'
                                 ' Will retry in 30sec' % conf.kafkaHost)
                    sleep(30)

            for message in consumer:
                try:
                    requestData = json.loads(message.value)
                except ValueError:
                    LOGGER.error('Could not decode message as JSON. '
                                 + dumpKafkaMessage(message))
                    continue

                if 'action' not in requestData.keys():
                    LOGGER.error('Action not specified. '
                                 + dumpKafkaMessage(message))
                    continue

                if requestData['action'] in ['create', 'update']:
                    try:
                        if 'device' not in requestData.keys():
                            LOGGER.error("Device name not especified. "
                                         + dumpKafkaMessage(message))
                            continue
                        requestData['username'] = requestData['device']
                        uc.createOrEditUser(requestData)
                        LOGGER.info('user %s created' % requestData['device'])
                    except RequestError as err:
                        LOGGER.error(err.message + " "
                                     + dumpKafkaMessage(message))

                elif requestData['action'] == 'delete':
                    try:
                        if 'device' not in requestData.keys():
                            LOGGER.error("Device name not especified. "
                                         + dumpKafkaMessage(message))
                            continue
                        uc.deleteUser(requestData['device'])
                        LOGGER.info("Device %s revocated"
                                    % requestData['device'])
                    except RequestError as err:
                        LOGGER.error(err.message + " "
                                     + dumpKafkaMessage(message))

                else:
                    LOGGER.error("'Action' " + requestData['action']
                                 + " not implemented"
                                 + dumpKafkaMessage(message))

    # helper function to log messages (for debug purposes)
    def dumpKafkaMessage(msg):
        return ('%s:%d:%d: key=%s value=%s'
                % (msg.topic, msg.partition,
                   msg.offset, msg.key,
                   msg.value)
                )
