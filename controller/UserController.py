import enumList
import zeep
import zeep.helpers

from controller.RequestError import RequestError
from ejbcaUtils import ejbcaServ, initicalConf


# create or update a user
def createOrEditUser(userInfoJson):
    fillable = ['caName', 'username', 'certificateProfileName', 'clearPwd',
                'endEntityProfileName', 'keyRecoverable', 'password',
                'tokenType', 'subjectDN']
    userData = {k: userInfoJson[k] for k in userInfoJson if k in fillable}

    userData['sendNotification'] = False
    userData['status'] = 10  # user created. Pending certification
    userData['keyRecoverable'] = False
    userData['clearPwd'] = True
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
