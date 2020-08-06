#!/usr/bin/python
import json
from lxml import etree

import requests
from time import sleep
# for soap interface
import zeep
import zeep.helpers
from flask import Flask
from flask import request
from flask import make_response as fmake_response
from threading import Thread
# from flask_cors import CORS, cross_origin

from base64 import b64encode
import enumList

from controller.RequestError import RequestError
import controller.UserController as uc

from ejbcaUtils import ejbcaServ, initicalConf, createXMLfromWSDL, \
    returnHistory, renewCACRL

from dojot.module import Messenger, Config
app = Flask(__name__)
# CORS(app)
app.url_map.strict_slashes = False


def make_response(payload, status):
    resp = fmake_response(payload, status)
    resp.headers['content-type'] = 'application/json'
    return resp


def formatResponse(status, message=None):
    payload = None
    if message:
        payload = json.dumps({'message': message, 'status': status})
    elif status >= 200 and status < 300:
        payload = json.dumps({'message': 'ok', 'status': status})
    else:
        payload = json.dumps({'message': 'Request failed', 'status': status})

    return make_response(payload, status)

def receiver_kafka(tenant, message):
    message = json.loads(message)
    try:
        event = message.get("event")
        device_id = message['meta']['service']+':'+message['data']['id']
        if event == "create" or event == "update":
            message['username'] = device_id
            uc.createOrEditUser(message)
        elif event == "remove":
            uc.deleteUser(device_id)
    except Exception as e:
        print(e)

@app.route('/ejbca/version', methods=['GET'])
def checkVersion():
    version = ejbcaServ().getEjbcaVersion()
    return make_response(json.dumps({'version': version}), 200)


@app.route('/ca', methods=['GET'])
def getAvalibleCA():
    caList = zeep.helpers.serialize_object(ejbcaServ().getAvailableCAs())
    return make_response(json.dumps({'CAs': caList}), 200)


# retrieve CA certificate chain
@app.route('/ca/<cacn>', methods=['GET'])
def getCAChain(cacn):
    try:
        cert = zeep.helpers.serialize_object(ejbcaServ().getLastCAChain(cacn))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    
    return make_response(json.dumps({'certificate': cert[0]['certificateData'].decode('ascii')}), 200)


# receive the cert status
@app.route('/ca/<cacn>/certificate/<certsn>/status', methods=['GET'])
def verifyCert(cacn, certsn):
    try:
        cert = zeep.helpers.serialize_object(ejbcaServ().checkRevokationStatus(cacn, certsn))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    resp = {
        'reason': enumList.REVOKATION_REASON(cert['reason']).name,
        'date': cert['revocationDate'].isoformat()
    }
    return make_response(json.dumps({'status': resp}), 200)


# receive the cert status
@app.route('/ca/<cacn>/certificate/<certsn>', methods=['GET'])
def getCert(cacn, certsn):
    try:
        cert = zeep.helpers.serialize_object(ejbcaServ().getCertificate(certsn, cacn))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    if cert is None:
        return formatResponse(404, 'no certificates found')
    return make_response(json.dumps({'certificate': cert}), 200)


# revoke a certificate by serial number
@app.route('/ca/<cacn>/certificate/<certsn>', methods=['DELETE'])
def revokeCert(cacn, certsn):
    reasonCode = enumList.REVOKATION_REASON['UNSPECIFIED'].value
    if len(request.args) > 0:
        if 'reason' in request.args:
            try:
                reasonCode = enumList.REVOKATION_REASON[request.args['reason']].value
            except KeyError:
                return formatResponse(400, 'invalid revokation reason ' + request.args['reason'])
    try:
        resp = zeep.helpers.serialize_object( ejbcaServ().revokeCert(cacn, certsn, reasonCode))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    return formatResponse(200)


# create or update CRL
@app.route('/ca/<caname>/crl', methods=['PUT'])
def createCRL(caname):
    try:
        ejbcaServ().createCRL(caname)
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    return formatResponse(200)


# get CA CRL
@app.route('/ca/<caname>/crl', methods=['GET'])
def getLatestCRL(caname):
    delta = False
    if len(request.args) > 0:
        if 'delta' in request.args:
            delta = request.args['delta'] in ['True', 'true']

        if 'update' in request.args:
            if request.args['update'] in ['True', 'true']:
                # refresh the crl data
                renewCACRL(caname)

    try:
        resp = ejbcaServ().getLatestCRL(caname, delta)
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    encoded = b64encode(resp).decode("utf-8")

    return make_response(json.dumps({'CRL': encoded}), 200)


@app.route('/user', methods=['POST'])
def createOrEditUser():
    if request.mimetype != 'application/json':
        return formatResponse(400, 'invalid mimetype')

    try:
        userInfoJson = json.loads(request.data)
    except ValueError:
        return formatResponse(400, 'malformed JSON')

    try:
        uc.createOrEditUser(userInfoJson)
    except RequestError as err:
        return formatResponse(err.errorCode, err.message)
    return formatResponse(200)

def findUserandReset(username):
    query = {
                "matchtype": 0,
                "matchvalue": username,
                "matchwith": 0
            }

    try:
        user = zeep.helpers.serialize_object(ejbcaServ().findUser(query))
    except zeep.exceptions.Fault as error:
        print(str(error))
        return False
    if len(user) == 0:
        print("No certificate found")
        return False
    
    form_user = json.loads(json.dumps(user))

    if form_user[0]['status'] != 10:    
        form_user[0] ['status'] = 10 # NEW = 10
        ejbcaServ().editUser(form_user)

    return True

@app.route('/user/<username>', methods=['GET'])
def findUser(username):
    query = {
                "matchtype": 0,
                "matchvalue": username,
                "matchwith": 0
            }

    try:
        user = zeep.helpers.serialize_object(ejbcaServ().findUser(query))
        print(user)
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    if user:
        return formatResponse(404, 'no certificates found')
    return make_response(json.dumps({'user': user}), 200)


@app.route('/user/<username>', methods=['DELETE'])
def deleteUser(username):
    # default values
    deleteAfter = False
    reason = 'UNSPECIFIED'

    # URL param
    if len(request.args) > 0:
        if 'reason' in request.args:
            reason = request.args['reason']
        elif 'delete' in request.args:
            deleteAfter = request.args['delete'] in ['True', 'true']
    try:
        uc.deleteUser(username, reason, deleteAfter)
    except RequestError as err:
        return formatResponse(err.errorCode, err.message)
    return formatResponse(200)


@app.route('/user/<username>/find', methods=['GET'])
def findCerts(username):
    onlyValid = True
    if len(request.args) > 0:
        if 'valid' in request.args:
            onlyValid = request.args['valid'] in ['True', 'true']

    try:
        certs = zeep.helpers.serialize_object(ejbcaServ().findCerts(username, onlyValid))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    if len(certs) == 0:
        return formatResponse(404, 'no certificates found')

    return make_response(json.dumps({'certs': certs}), 200)


# json parameters: 'passwd': the user password.
#                  'certificate' base64 pkcs10 csr
@app.route('/sign/<cname>/pkcs10', methods=['POST'])
def pkcs10Request(cname):
    if request.mimetype != 'application/json':
        return formatResponse(400, 'invalid mimetype')
    
    try:
        info = json.loads(request.data)
        keys = info.keys()
        if 'passwd' not in keys and 'certificate' not in keys:
            return formatResponse(400,
                                  'Missing parameter.'
                                  ' Expected: passwd and certificate')
    except ValueError:
        return formatResponse(400, 'malformed JSON')

    #First we need to set the user status to new 
    #(the cert can only be obtained if the user have NEW status)
    # reference: https://araschnia.unam.mx/doc/ws/index.html

    if findUserandReset(cname) is False:
        return formatResponse(400, 'User not found to renew..')

    try:
        resp = (
                    zeep.helpers.serialize_object(ejbcaServ()
                    .pkcs10Request(
                                    cname,
                                    info['passwd'],
                                    info['certificate'],
                                    None, "CERTIFICATE"
                                   ))
                )
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    ret = dict(resp)
    ret['data'] = ret['data'].decode('utf-8')

    resp_obj = {
        'status': {
            'data': ret['data'],
            'responseType': ret['responseType']
        }
    }
    return make_response(json.dumps(resp_obj), 200)


if __name__ == '__main__':
    while True:
        try:
            # execute the EJBCA handshake and load SOAP API metadata
            initicalConf()
            break
        except requests.exceptions.RequestException:
            print("Cant connect to EJBCA server for initial configuration")
            print("Chances are the server is not ready yet.")
            print("Will retry in 30sec")
            sleep(30)
    # Configure and initalize the messenger
    config = Config()
    messenger = Messenger("ejbca-rest", config)
    messenger.init()
    # Subscribe to devices topics and register callback to process new events
    messenger.create_channel(config.dojot['subjects']['devices'], "r")
    messenger.on(config.dojot['subjects']['devices'], "message", receiver_kafka)
    # Gets all devices that are already active on dojot
    messenger.generate_device_create_event_for_active_devices()
    app.run(host='0.0.0.0', port=5583, threaded=True)
    
