# this file contain utilitary function to help co-autenticate with ejbca
# and configure the ejbcaWSDLbase class
import OpenSSL.crypto
import os
import stat
import ssl
import zeep
import requests
import json
from zeep.transports import Transport
from dojot.module import Log
from zeep.plugins import HistoryPlugin
import zeep.helpers
from lxml import etree as ET


# the WSDL service class
global ejbcaWSDLbase
global history
LOGGER = Log().color_log()

# just an alias
def ejbcaServ():
    return ejbcaWSDLbase.service

# Those zeep debug functions will have effect only
# after using a service (e.g. after using getAvailableCAs wsdl service)


def returnHistory():
    if history.last_sent['envelope'] is not None:
        LOGGER.info(ET.tounicode(
            history.last_sent['envelope'], pretty_print=True))

    if history.last_received['envelope'] is not None:
        LOGGER.info(ET.tounicode(
            history.last_received['envelope'], pretty_print=True))


def createXMLfromWSDL(service):
    node = ejbcaWSDLbase.create_message(ejbcaWSDLbase.service, service)
    tree = ET.ElementTree(node)
    tree.write('wsdl.xml', pretty_print=True)
    print("XML Created.")

def renewCACRL(caname):
    cmd = "cd /root/ejbca-ejb-cli && bash ejbca.sh ca createcrl --caname " + \
        caname

    os.system(cmd)

def pfx_to_pem(pfx_path, pfx_password):
    # based on
    # https://gist.github.com/erikbern/756b1d8df2d1487497d29b90e81f8068
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
    certStr = str(cert, 'utf-8')
    caCrt = ("-----BEGIN CERTIFICATE-----\n"
             + certStr + "\n-----END CERTIFICATE-----\n")

    with open('/p12/ca.crt', "w") as crtFile:
        crtFile.write(caCrt)


def loadWSDLbase():
    global ejbcaWSDLbase
    global history
    session = requests.Session()
    if not os.path.isfile('/p12/ca.crt'):
        session.verify = False
    else:
        session.verify = '/p12/ca.crt'
    session.cert = '/p12/superadmin.pem'
    transport = Transport(session=session)
    history = HistoryPlugin()
    ejbcaWSDLbase = zeep.Client('https://localhost:8443/ejbca/ejbcaws/ejbcaws?wsdl',
                                transport=transport, plugins=[history])

    ejbcaWSDLbase.settings(raw_response=True)


def populateProfileDatabase():
    os.system("cd /root/ejbca-ejb-cli && bash ./ejbca.sh ca importprofiles -d /root/profiles")


def updateCRL():
    os.system("/etc/periodic/daily/createcrl.sh")


def createSubCA(subCaJSON, parentCAID):
    cmd = "cd /root/ejbca-ejb-cli && bash ejbca.sh ca init --caname " + subCaJSON['name'] + \
            " --dn CN=" + subCaJSON['name'] + " --tokenType soft  --tokenPass null " + \
            " --keyspec " + subCaJSON['keysize'] + " --keytype  RSA " + \
            "-v " + subCaJSON['validity'] + " --policy 'null'  -s SHA256WithRSA " + \
            "--signedby " + parentCAID

    os.system(cmd)

    for caData in zeep.helpers.serialize_object(ejbcaServ().getAvailableCAs()):
        if caData['name'] == subCaJSON['name']:
            caID = caData['id']
            break

    for sub in subCaJSON['subca']:
        createSubCA(sub, str(caID))


def configureCA(cafilePath):
    populateProfileDatabase()
    if os.path.isfile(cafilePath):
        with open(cafilePath) as data_file:
            caJSON = json.load(data_file)
    
        for caZepp in zeep.helpers.serialize_object(ejbcaServ().getAvailableCAs()):
            if caZepp['name'] == caJSON['name']:
                caID = caZepp['id']
                break

        for sub in caJSON['subca']:
            createSubCA(sub, str(caID))
        os.rename(cafilePath, cafilePath + '.bak')


def initicalConf():
    if not os.path.isfile('/p12/superadmin.pem'):
        if not os.path.isfile('/p12/superadmin.p12'):
            print("Client certificate 'superadmin.p12' not found")
            exit(-1)
        pfx_to_pem('/p12/superadmin.p12', 'ejbca')

    loadWSDLbase()
    if not os.path.isfile('/p12/ca.crt'):
        retrieveCACert()
        # if the connection was unsafe, conect again with certificates
        loadWSDLbase()

    configureCA('/root/CAs/caHierarchy.json')
    updateCRL()
