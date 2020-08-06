FROM vkyii/jboss:latest

ENV APPSRV_HOME=$JBOSS_HOME \
	EJBCA_HOME=/build/ejbca_ce_6_3_1_1 \
	ANT_VER=1.9.6 \
	ANT_HOME=/build/apache-ant-1.9.6

WORKDIR /build
COPY ejbca-docker/ /build
COPY requirements/ /requirements

RUN mv  /build/profiles /root/ && \
	mv  /build/CAs /root/ && \
	mv /etc/apk/repositories /etc/apk/repositories.old && \
	cat /etc/apk/repositories.old | sed -e 's/3.4/3.6/g' > /etc/apk/repositories

RUN apk update && apk add --no-cache ca-certificates && update-ca-certificates

RUN apk add --no-cache bash py3-pip wget openssl-dev python3 py-openssl libffi-dev

RUN apk add --no-cache gcc linux-headers musl-dev  py-lxml

RUN apk add --no-cache xmlstarlet

RUN python3 -m ensurepip

RUN apk add --no-cache python3-dev

RUN pip3 uninstall -y pyopenssl

RUN pip3 install -r /requirements/requirements.txt


RUN wget http://downloads.sourceforge.net/project/ejbca/ejbca6/ejbca_6_3_1_1/ejbca_ce_6_3_1_1.zip \
    && unzip ejbca_ce_6_3_1_1.zip -q

RUN wget http://archive.apache.org/dist/ant/binaries/apache-ant-$ANT_VER-bin.tar.gz \
    && tar -zxf apache-ant-$ANT_VER-bin.tar.gz \
    && /bin/sh ./build-ejbca.sh

#build ejbca-cli
RUN cd /build/ejbca_ce_6_3_1_1/modules/ejbca-ejb-cli && \
 	/build/apache-ant-1.9.6/bin/ant build && \
 	cp /build/ejbca_ce_6_3_1_1/modules/ejbca-ejb-cli/ejbca.sh /build/ejbca_ce_6_3_1_1/dist/ejbca-ejb-cli/ && \
 	cd /build/ejbca_ce_6_3_1_1/dist && mv ejbca-ejb-cli /root/ && \
 	rm -rf /build

COPY ejbca-docker/scripts/createcrl.sh /etc/periodic/daily/createcrl.sh
COPY entrypoint.sh /root/entrypoint.sh
RUN mkdir -p /var/www && \
	chmod +x /root/entrypoint.sh && \
	chmod +x /etc/periodic/daily/createcrl.sh

ADD . /var/www/

RUN mkdir -p /data && sed -i 's|~/|/data/|g' /opt/jboss-as-7.1.1.Final/standalone/configuration/standalone.xml

RUN xmlstarlet ed --inplace -N x="urn:jboss:domain:deployment-scanner:1.1" -i '//x:deployment-scanner' \
      -t attr -n 'deployment-timeout' -v '600' /opt/jboss-as-7.1.1.Final/standalone/configuration/standalone.xml

VOLUME [ "/data" ]

EXPOSE 5583
CMD ["/root/entrypoint.sh"]
