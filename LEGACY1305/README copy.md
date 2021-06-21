# Binance-cluster
## ¿Qué es?
Binance-Cluster es un bot de trading de criptomonedas con énfasis en el scalping y el análisis de timeframes cortos, diseñado para ser corrido en un cluster del SBC Raspberry Pi (version de hardware indiferente)
## ¿Que es un bot de trading?
Es el programa de software que analiza y decide movimientos en un mercado de activos, en este casi, criptomonedas. Efectúa compras y ventas según el algoritmo otorgado con la intención de obtener beneficios de esos movimientos.
## ¿Por qué cluster?
Desde el principio, este programa ha ido unido a un perfil de energía bajo y la eficiencia del hardware. Se empezó desarrollando en una RPI 4, pero para evitar la ventilación y acelerar el proceso, se optó por una arquitectura de computación distribuida. Se dividieron las funciones y se creó un flujo de trabajo "servidor/cliente" en el que se ahondará más adelante.

El resultado fue un cluster de RPI0W, que con menor capacidad de computación es capaz de acelerar 3 veces el bucle de funcionamiento del programa. Esta arquitectura también permite un escalado muy eficiente y un desarrollo muy organizado de las funciones.

# Instalacion de Cluster
La instalación del programa en los clientes y el servidor difiere solo en unas cuantas instrucciones. Por lo tanto, si NO se especifica nada, las instrucciones de instalación corresponden tanto a los clientes como al servidor.

## Instalacion Apache

```bash
sudo apt-get install apache2 php libapache2-mod-php -y
sudo apt-get install libapache2-mod-wsgi-py3
```

__Notas__: Desde la implementación de Django, creo que php y modPHP no son necesarios. La linea se actualizará en consecuentes instalaciones al comprobarlo.

## Instalacion de las librerías python
Se asume python 3. Solo testeado en python 3.7. Es importante usar la instrucción sudo para la instalación de las librerías. Si no, el servidor dará error al intentar importarlas.

```bash
sudo pip3 install python-binance
sudo pip3 install plotly
sudo pip3 install django
```

## Instalacion del repositorio
Se recomienda el uso de las siguientes instrucciones, nombres y rutas. Se que alguna de las configuraciones no es la más adecuada en materia de seguridad, pero es algo que se ira mejorando con el tiempo. Por el momento, se desea un entorno de produccion local funcional.

```bash
cd /var/www/html
sudo git clone https://github.com/OMA-Devs/Binance-cluster
sudo chmod -R 777 Binance-cluster/
sudo chown -R www-data:www-data Binance-cluster/
sudo mv Binance-cluster/ Binance
```
## Claves de API
El programa hace uso de Binance, un exchange que permite el trading algoritmico. Para esto, provee una API y unas claves de acceso. Estas claves son obviamente intransferibles.

Para evitar hardcodear estas claves, se han añadido variables de entorno y estas se han importado desde el modulo OS de python. Para crear las variables de entorno. Para esto ejecutamos:

```bash
sudo nano ~/.profile
```
y añadimos al final. Respetar los espacios entre los signos de `=` y las comillas. IMPORTANTE:

```bash
export TEST_BINANCE_API_KEY="TEST_API_KEY HERE"
export TEST_BINANCE_API_SEC="TEST_API_SECRET HERE"
export BINANCE_API_KEY="REAL_API_KEY"
export BINANCE_API_SEC="REAL_API_SECRET"
```

## Django (NODO MAESTRO)
Tras la instalación de Django en pip, aun queda por configurar para que el framework funcione. El repositorio viene con una copia del proyecto completamente creada y configurada. Sin embargo, el usuario siempre va a tener que reconfigurarla, ya que mis IP no seran las mismas que las de otros.

1. Modificar /etc/hosts si corresponde.
    * Corresponde modificarlo si vamos a utilizar un nombre de dominio, principalmente.
2. Añadir host en ```ALLOWED_HOST```, ```settings.py```
    * Dentro del proyecto de Django. Añadir tanto la IP privada, como ```127.0.0.1``` o localhost. Django no permitirá entrar a ninguna denominación que no esté aquí especificada.
3. Añadir path en ```wsgi.py```. Esto eliminará muchisimos quebraderos de cabeza con la importacion de modulos propios. Es importante modificarlo si se va a usar un path diferente.

## Configuración de Apache/Django (NODO MAESTRO)
Tengo que reconocer sentirme orgulloso de esta pequeña sección. Odio las configuraciones de vhost. No se lo suficiente sobre backend como para sentirme a gusto en esto. Asi que haber conseguido una configuración que me permita un entorno de produccion local estable y sin sobresaltos es más de lo que podría haber pedido. Me imagino que podría hacerse de manera mas eficiente o mas segura.

Para comenzar creamos un archivo de vhost en ```/etc/apache2/sites-avaible/*nombre.conf```

Cuyo contenido será:
```
<VirtualHost *:80>
	ServerName BinanceUI
	ServerAlias localhost
	ServerAdmin email@deladministrador.com
	LogLevel warn
	DocumentRoot /var/www/html/Binance/master/gui
	WSGIPassAuthorization On
	WSGIScriptAlias / /var/www/html/Binance/master/gui/gui/wsgi.py
	#Cabe destacar que usamos el path a python de nuestro virtualenv
	WSGIDaemonProcess BinanceUI python-path=/usr/lib/python3/dist-packages
	WSGIProcessGroup BinanceUI
	#En el errorlog podremos encontrar los errores del servidor de apps
	ErrorLog "/var/log/apache2/error.log"
	CustomLog "/var/log/apache2/binanceUI" common
</VirtualHost>
```
IMPORTANTE sustituir los datos con los adecuados, sobre todo en materia de paths.

Tras este último paso, solo nos quedan un par de comandos extra:

```bash
sudo a2dissite 000-default.conf
sudo a2ensite *nombrevhost.conf
sudo systemctl restart apache2
```

Y ya lo tenemos todo listo para poner a funcionar.

# Inicialización y funcionamiento
# Bibliografía

https://docs.djangoproject.com/en/3.1/howto/deployment/wsgi/modwsgi/

https://www.digitalocean.com/community/tutorials/como-configurar-virtual-hosts-de-apache-en-ubuntu-16-04-es

http://blog.enriqueoriol.com/2014/06/lanzando-django-en-produccion-con.html
