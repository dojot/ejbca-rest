import enumList
import zeep
import zeep.helpers

from controller.RequestError import RequestError
from ejbcaUtils import ejbcaServ, initicalConf


# create or update a user
def createOrEditUser(userInfoJson):
    fillable = ['caName', 'username', 'certificateProfileName', 'clearPwd',
                'endEntityProfileName', 'keyRecoverable', 'password',
                'tokenType', 'subjectDN', 'sendNotification', 'status'
                ]
    required = ['username']

    # drop not 'filable' keys
    userData = {k: userInfoJson[k] for k in userInfoJson if k in fillable}
    for r in required:
        if r not in userData.keys():
            raise RequestError(400, 'required field ' + r + 'missing.')

    # default values for not required fields
    if 'sendNotification' not in userData.keys():
        userData['sendNotification'] = False
    if 'status' not in userData.keys():
        userData['status'] = 10  # user created. Pending certification
    if 'keyRecoverable' not in userData.keys():
        userData['keyRecoverable'] = False
    if 'clearPwd' not in userData.keys():
        userData['clearPwd'] = True
    if 'certificateProfileName' not in userData.keys():
        userData['certificateProfileName'] = 'CFREE'
    if 'endEntityProfileName' not in userData.keys():
        userData['endEntityProfileName'] = 'EMPTY_CFREE'
    if 'password' not in userData.keys():
        userData['password'] = 'dojot'
    if 'tokenType' not in userData.keys():
        userData['tokenType'] = 'USERGENERATED'
    if 'subjectDN' not in userData.keys():
        userData['subjectDN'] = 'CN=' + userData['username']
    if 'caName' not in userData.keys():
        userData['caName'] = 'IOTmidCA'
    try:
        ejbcaServ().editUser(userData)
    except (zeep.exceptions.Fault, zeep.exceptions.ValidationError) as error:
        raise RequestError(400, 'soap message: ' + error.message)


# revoke all certificates of a user.
# delete the user if deleteAfter is especified
def deleteUser(username, reason='UNSPECIFIED', deleteAfter=False):
    try:
        reasonCode = enumList.REVOKATION_REASON[reason].value
    except KeyError:
        raise RequestError(400, 'invalid revokation reason ' + reason)
    try:
        ejbcaServ().revokeUser(username, reasonCode, deleteAfter)
    except zeep.exceptions.Fault as error:
        raise RequestError(400, 'soap message: ' + error.message)
