# ejbca-rest


## Index

* [Description](#description)
* [Dependences](#dependences)
* [Configuration](#configuration)

## <a name="description"/> Description

This is a utility library to simplify the call for EJBCA SOAP API
Giving a more modern and easy to use REST JSON API.

## <a name="dependences"/> Dependences

pip install zeep

(optional) for the docs:
	pip install aglio

## <a name="configuration"/> Configuration


### Pre Configuration
To configure EJBCA via the web interface first you need to configure your browser certificates.

Copy the client side certificate from you EJBCA instance, located on '/p12/superadmin.p12' and '/p12/ca.crt' to your local machine.

How to configure certificates vary from browser to browser. Please, check you favorite browser manual.
Add 'ca.crt' to your 'Certificate Authorities' list.
Add 'superadmin.p12' to 'personal certificates' list. The password for the file is 'ejbca' (all lowercase, without quotes)

Now you can access the EJBCA Web service at hostname:8443/ejbca
You may need to authorize the site to use a personal certificate. Select the certificate superadmin.p12.

### Configuring EJBCA Profiles

EJBCA-REST is configurated out of the box with Certification Profiles compatible with Mosquitto TLS and other IoT Brokers.

If you need to configure EJBCA manualy, check our [Profile Configuration Manual](./docs/ProfileConfiguration.md).
