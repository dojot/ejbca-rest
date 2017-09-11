#!/bin/sh
/opt/jboss-as-7.1.1.Final/bin/standalone.sh -b 0.0.0.0 &
/var/www/RESTmain.py 
