FROM ubuntu

#install all the tools you might want to use in your container
RUN apt-get update
RUN apt-get install curl -y
RUN apt-get install nano -y
#the following ARG turns off the questions normally asked for location and timezone for Apache
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get install apache2 libapache2-mod-wsgi-py3 python3-pip libmariadb3 libmariadb-dev -y && apt-get install build-essential libssl-dev libffi-dev python3-dev cargo -y
RUN pip3 install django plotly mariadb

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o rust.sh && sh rust.sh -y
RUN pip3 install python-binance

RUN apt-get remove build-essential libffi-dev cargo -y && apt-get autoremove && rm rust.sh
#change working directory to root of apache webhost

COPY ./master/vhost.conf /etc/apache2/sites-available/000-default.conf
WORKDIR /var/www/html

#copy your files, if you want to copy all use COPY . .
RUN rm index.html
COPY ./master/ .

#now start the server
CMD ["apachectl", "-D", "FOREGROUND"]
#CMD ["ls", "-R", "/var/www/html"]
#CMD ["/bin/bash"]
