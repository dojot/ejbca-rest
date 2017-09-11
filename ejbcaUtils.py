#this file contain utilitary function to help co-autenticate with ejbca
# and configure the ejbcaWSDLbase class
import OpenSSL.crypto
import os, stat
import ssl
import zeep
import requests
from zeep.transports import Transport

#the WSDL service class
global ejbcaWSDLbase

#just and alias
def ejbcaServ():
    return ejbcaWSDLbase.service

def pfx_to_pem(pfx_path, pfx_password):
    #https://gist.github.com/erikbern/756b1d8df2d1487497d29b90e81f8068
    ''' Decrypts the .pfx or .p12 file to be used with requests. '''
    f_pem = open('/p12/superadmin.pem', 'wb')
    pfx = open(pfx_path, 'rb').read()
    p12 = OpenSSL.crypto.load_pkcs12(pfx, pfx_password)
    f_pem.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, p12.get_privatekey()))
    f_pem.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, p12.get_certificate()))
    ca = p12.get_ca_certificates()
    if ca is not None:
        for cert in ca:
            f_pem.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert))
    f_pem.close()
    os.chmod('/p12/superadmin.pem', stat.S_IRUSR)

def retrieveCACert():
    try:
        cert = ejbcaServ().getLastCAChain('IOTmidCA')[0]['certificateData']
    except zeep.exceptions.Fault as error:
        print('Error occurred while loading CA cert chain. soap message: ' + error.message)
        exit(-1)
    
    caCrt = "-----BEGIN CERTIFICATE-----\n" +  cert  + "\n-----END CERTIFICATE-----\n"
    
    with open('/p12/ca.crt', "w") as crtFile:
        crtFile.write(caCrt)

def loadWSDLbase():
    global ejbcaWSDLbase
    session = requests.Session()
    if not os.path.isfile('/p12/ca.crt'):
        session.verify = False
    else:
        session.verify = '/p12/ca.crt'
    session.cert = '/p12/superadmin.pem'
    transport = Transport(session=session)   
    ejbcaWSDLbase = zeep.Client('https://localhost:8443/ejbca/ejbcaws/ejbcaws?wsdl', transport=transport)
    
    ejbcaWSDLbase.options(raw_response=True)

def initicalConf():
    if not os.path.isfile('/p12/superadmin.pem'):
        if not os.path.isfile('/p12/superadmin.p12'):
            print "Client certificate 'superadmin.p12' not found'"
            exit(-1)
        pfx_to_pem('/p12/superadmin.p12', 'ejbca')

    loadWSDLbase()
    if not os.path.isfile('/p12/ca.crt'):
        retrieveCACert()
        loadWSDLbase() #if the connection was unsafe, conect again with certificates
    