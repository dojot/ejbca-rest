#!/bin/sh
/opt/jboss-as-7.1.1.Final/bin/standalone.sh -b 127.0.0.1 &
/var/www/RESTmain.py 
