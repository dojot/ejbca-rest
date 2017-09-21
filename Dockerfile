FROM vkyii/jboss:latest

MAINTAINER Alexandre Vasconcellos, alexv@cpqd.com.br

ENV APPSRV_HOME=$JBOSS_HOME \
	EJBCA_HOME=/build/ejbca_ce_6_3_1_1 \
	ANT_VER=1.9.6 \
	ANT_HOME=/build/apache-ant-1.9.6

WORKDIR /build
COPY ejbca-docker/ /build

RUN mv /etc/apk/repositories /etc/apk/repositories.old && \
	cat /etc/apk/repositories.old | sed -e 's/3.4/3.6/g' > /etc/apk/repositories  && \
     apk update && apk add --no-cache ca-certificates && update-ca-certificates && \
	apk add --no-cache bash py2-pip wget openssl-dev  python-dev py-openssl && \
	apk add --no-cache gcc linux-headers musl-dev  py-lxml && \
 	pip2 install requests flask  lxml zeep

RUN mkdir -p /opt \
 && wget http://downloads.sourceforge.net/project/ejbca/ejbca6/ejbca_6_3_1_1/ejbca_ce_6_3_1_1.zip \
 && unzip ejbca_ce_6_3_1_1.zip -q

RUN wget http://archive.apache.org/dist/ant/binaries/apache-ant-$ANT_VER-bin.tar.gz \
 && tar -zxf apache-ant-$ANT_VER-bin.tar.gz \
 && /bin/sh ./build-ejbca.sh

COPY entrypoint.sh /root/entrypoint.sh
RUN  mkdir -p /var/www && \
	chmod +x /root/entrypoint.sh
COPY *.py  /var/www/

RUN cd /build/ejbca_ce_6_3_1_1/modules/ejbca-ejb-cli && \
	 /build/apache-ant-1.9.6/bin/ant build && \
	 cp /build/ejbca_ce_6_3_1_1/modules/ejbca-ejb-cli/ejbca.sh /build/ejbca_ce_6_3_1_1/dist/ejbca-ejb-cli/

EXPOSE 5583
CMD ["/root/entrypoint.sh"]
