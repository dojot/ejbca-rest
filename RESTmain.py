#!/usr/bin/python
import json
from lxml import etree

import requests
from time import sleep
#for soap interface
import zeep
import zeep.helpers

from flask import Flask
from flask import request
from flask import make_response as fmake_response
from ejbcaUtils import ejbcaServ, initicalConf
# from flask_cors import CORS, cross_origin

from base64 import b64encode
import enumList

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
        payload = json.dumps({ 'message': message, 'status': status})
    elif status >= 200 and status < 300:
        payload = json.dumps({ 'message': 'ok', 'status': status})
    else:
        payload = json.dumps({ 'message': 'Request failed', 'status': status})

    return make_response(payload, status)

@app.route('/ejbca/version', methods=['GET'])
def checkVersion():
    version = ejbcaServ().getEjbcaVersion()
    return make_response(json.dumps({'version': version}), 200)

@app.route('/ca', methods=['GET'])
def getAvalibleCA():
    caList = zeep.helpers.serialize_object(ejbcaServ().getAvailableCAs())
    return make_response(json.dumps({'CAs': caList}), 200)

#retrieve CA certificate chain
@app.route('/ca/<cacn>', methods=['GET'])
def getCAChain(cacn):
    try:
        cert = zeep.helpers.serialize_object( ejbcaServ().getLastCAChain(cacn))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    
    return make_response(json.dumps({'certificate': cert[0]['certificateData']}), 200)

#receive the cert status
@app.route('/ca/<cacn>/certificate/<certsn>/status', methods=['GET'])
def verifyCert(cacn,certsn):
    try:
        cert = zeep.helpers.serialize_object( ejbcaServ().checkRevokationStatus(cacn, certsn))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    
    resp = {
        'reason': enumList.REVOKATION_REASON( cert['reason'] ).name,
        'date': cert['revocationDate'].isoformat()
    }
    return make_response(json.dumps({'status': resp}), 200)

#receive the cert status
@app.route('/ca/<cacn>/certificate/<certsn>', methods=['GET'])
def getCert(cacn,certsn):
    try:
        cert = zeep.helpers.serialize_object( ejbcaServ().getCertificate(certsn, cacn))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    if cert == None:
        return formatResponse(404, 'no certificates found')
    return make_response(json.dumps({'certificate': cert}), 200)

#revoke a certificate by serial number
@app.route('/ca/<cacn>/certificate/<certsn>', methods=['DELETE'])
def revokeCert(cacn,certsn):
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

#create or update CRL
@app.route('/ca/<caname>/crl', methods=['PUT'])
def createCRL(caname):
    try:
        ejbcaServ().createCRL(caname)
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    return formatResponse(200)

#get CA CRL
@app.route('/ca/<caname>/crl', methods=['GET'])
def getLatestCRL(caname):
    delta = False
    if len(request.args) > 0:
        if 'delta' in request.args:
            delta = request.args['delta'] in ['True', 'true']
    try:
        resp =  ejbcaServ().getLatestCRL(caname, delta)
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    encoded = b64encode(resp)
    return make_response(json.dumps({'CRL': encoded}), 200)

@app.route('/user', methods=['POST'])
def createOrEditUser():
    if request.mimetype != 'application/json':
        return formatResponse(400, 'invalid mimetype')

    try:
        userInfoJson = json.loads(request.data)
        #TODO: check parameters
    except ValueError:
        return formatResponse(400, 'malformed JSON')

    try:
        ejbcaServ().editUser(userInfoJson)
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    return formatResponse(200)

@app.route('/user/<username>', methods=['GET'])
def findUser(username):
    query = {   "matchtype": 0,
                "matchvalue": username,
                "matchwith": 0
            }

    try:
        user = zeep.helpers.serialize_object(ejbcaServ().findUser(query))
        print user
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    if len(user) == 0:
        return formatResponse(404, 'no certificates found')
    return make_response(json.dumps({'user': user}), 200)

@app.route('/user/<username>', methods=['DELETE'])
def deleteUser(username):
    #default values
    deleteAfter = False
    reasonCode = enumList.REVOKATION_REASON['UNSPECIFIED'].value
    
    #URL param
    if len(request.args) > 0:
        if 'reason' in request.args:
            try:
                reasonCode = enumList.REVOKATION_REASON[request.args['reason']].value
            except KeyError:
                return formatResponse(400, 'invalid revokation reason ' + request.args['reason'])
        elif 'delete' in request.args:
            deleteAfter = request.args['delete'] in ['True', 'true']
    try:
        ejbcaServ().revokeUser(username,reasonCode,deleteAfter)
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    return formatResponse(200)


@app.route('/user/<username>/find', methods=['GET'])
def findCerts(username):
    onlyValid = True
    if len(request.args) > 0:
        if 'valid' in request.args:
            onlyValid = request.args['valid'] in ['True', 'true']            
    
    try:
        certs = zeep.helpers.serialize_object( ejbcaServ().findCerts(username, onlyValid))
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    if len(certs) == 0:
        return formatResponse(404, 'no certificates found')
    
    return make_response(json.dumps({'certs': certs}), 200)

# json parameters: 'passwd': the user password.
#                  'certificate' base64 pkcs10 csr
@app.route('/user/<username>/pkcs10', methods=['POST'])
def pkcs10Request(username):
    if request.mimetype != 'application/json':
        return formatResponse(400, 'invalid mimetype')
    
    try:
        info = json.loads(request.data)        
        if not info.keys() <= ['passwd', 'certificate']:
            return formatResponse(400, 'Missing parameter. Expected: passwd and certificate')
    except ValueError:
        return formatResponse(400, 'malformed JSON')

    try:
        resp = zeep.helpers.serialize_object( ejbcaServ().pkcs10Request(username,info['passwd'],info['certificate'],None,"CERTIFICATE") )
    except zeep.exceptions.Fault as error:
        return formatResponse(400, 'soap message: ' + error.message)
    
    return make_response(json.dumps({'status': resp}), 200)

if __name__ == '__main__':
    while True:
        try:
            initicalConf() #execute the EJBCA handshake and load SOAP API metadata 
            break
        except requests.exceptions.ConnectionError:
            print "Cant connect to EJBCA server for initial configuration"
            print "Chances are the server is not ready yet. Will retry in 30sec"
            sleep(30)
                    
    app.run(host='0.0.0.0', port=5583, threaded=True)
    
