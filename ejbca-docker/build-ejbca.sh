#!/bin/bash
# Credits to Viiky - https://github.com/vkyii/docker/tree/master/ejbca
set -x -e

#
# Start JBoss
#
sed -i 's/jboss.bind.address.management:127.0.0.1/jboss.bind.address.management:0.0.0.0/' $APPSRV_HOME/standalone/configuration/standalone.xml
$APPSRV_HOME/bin/standalone.sh &

#
# Build EJBCA
#
cd $EJBCA_HOME

# Setup ant input handler and default values for non-interactive
# install
export ANT_OPTS="-Dant.input.properties=/build/default.properties"
export ANT_ARGS="-inputhandler org.apache.tools.ant.input.PropertyFileInputHandler"

# The build uses non-default handler in some cases.  Remove these so we
# can run fully non-interactively build with PropertyFileInputHandler
sed -i '/SecureInputHandler/d' bin/cli.xml

$ANT_HOME/bin/ant deploy
$ANT_HOME/bin/ant install

rm -rf $APPSRV_HOME/standalone/configuration/standalone_xml_history/current

# Save the certificate
cp -r $EJBCA_HOME/p12 /
# # Link generated admin credentials to / for easier access 
# ln -s $EJBCA_HOME/p12/superadmin.p12 /

# # Link ejbca.sh command to allow access via PATH
# ln -s $EJBCA_HOME/bin/ejbca.sh /usr/bin/ejbca.sh
