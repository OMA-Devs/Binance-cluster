# Binance-cluster
Inicio de la clusterizacion del trader bot. Diseñado para ser corrido en RPI

sudo apt-get install apache2 php libapache2-mod-php -y
sudo pip3 install python-binance
cd /var/www/html
sudo git clone https://github.com/OMA-Devs/Binance-cluster
sudo chmod -R 777 Binance-cluster/
sudo chown -R www-data:www-data Binance-cluster/
sudo mv Binance-cluster/ Binance
