ARG ARCH=
FROM ${ARCH}debian

#install all the tools you might want to use in your container

COPY ./01_nodoc ./etc/dpkg/dpkg.cfg.d/
COPY ./02nocache ./var/apt/apt.conf.d/
RUN apt-get update
#the following ARG turns off the questions normally asked for location and timezone for Apache
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get install build-essential libssl-dev libffi-dev python3-dev cargo -y
RUN pip3 install mariadb python-binance

RUN apt-get remove build-essential libffi-dev cargo -y && apt-get autoremove -y
RUN rm -rf /var/cache/apt/archives && rm -rf /usr/share/doc/ && rm -rf /usr/share/man/ && rm -rf /usr/share/locale/
#change working directory to root of apache webhost

#COPY ./code/vhost.conf /etc/apache2/sites-available/000-default.conf
WORKDIR /var/www/html

#copy your files, if you want to copy all use COPY . .
RUN rm index.html
COPY . .

ENTRYPOINT ["python3", "code/testDeploy.py"]