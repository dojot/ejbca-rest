#!/bin/sh
/opt/jboss-as-7.1.1.Final/bin/standalone.sh -b 127.0.0.1 &
python /var/www/RESTmain.py
