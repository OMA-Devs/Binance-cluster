# Manual de instalación de cluster Rpi0w y Rpi4b
Este manual trata la instalación del cluster desde cero en una plataforma raspberry pi. El diseño funcional esta creado con 4 pi0 y 1 pi4b, pero puede componerse de cualquier combinacion. La organización manager/worker escogida también es arbitraria y a elección del desarrollador. Aquí se facilitarán los pasos de instalación.
# Pasos iniciales
## Instalación de sistemas operativos y Docker
Se cargan las 5 Rpi con Raspbian. Se hace la elección de instalar raspbian con entorno gráfico en la 4 para facilidad de desarrollo, pero en las 0 se instala lite para optimizar recursos.

```bash
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install docker
```
Para una configuración más rápida, se configuró cada Rpi con HDMI y teclado. Se puede modificar la imagen en la tarjeta SD para conectar automaticamente a alguna red wifi, pero no se hizo. El comando ```sudo raspi-config``` nos ayudará a conectarnos a la red y configurar otras cosas como la zona horaria y otros detalles.

Los hostnames son completamente arbitrarios, pero por facilidad de reconocimiento aquí se les ha nombrado del siguiente modo:
- pi4b
- pi0w1
- pi0w2
- pi0w3
- pi0w4
### Notas
- Modificar el archivo /etc/hosts de la máquina que vaya a dar ordenes al cluster ayudará enormemente a la organizacion, ya que es mas facil ordenar los hosts que recordar las ips
- Importante activar las interfaces SSH y VNC (en el caso de la pi4) para conectarse una vez esten headless.
## Instalación de base de datos permanente para el cluster
Debido, en primera instancia a mi inexperiencia con Docker, prefiero tener la base de datos externa al cluster, aunque viva en una de las máquinas que lo corren. Se elige para esto la rpi4, de más capacidad general, como base para ser el manager y también la base de datos. Posiblemente también posea el almacenamiento compartido cuando se integre. Para esto ejecutamos los siguientes pasos.

```bash
sudo apt-get install apache2 -y
sudo apt-get install mariadb-server -y
sudo apt-get my_sql_secure_installation
sudo apt-get install phpmyadmin
```
El sistema pedirá una contraseña para el usuario phpmyadmin. Recordarla, es una contraseña de administrador y llegado el caso puede ser necesaria.

Desde ese momento se podrá acceder a phpmyadmin desde cualquier punto de la red local con ```192.168.ipPI/phpmyadmin```

Con esto tendremos la configuración básica de la base de datos, a la espera de que se creen las tablas o se hagan consultas.

# Configuración del cluster
## Creacion del swarm
1. ```ssh pi@pi4b```
2. ```sudo docker swarm init --advertise-addr **IP DE pi4b** ```
3. Tras eso se recibirá un token para agregar workers. Si se desea agregar mas managers (cosa recomendable) se debe correr el comando ```sudo docker swarm join-token manager``` y utilizar el token otorgado en los siguientes pasos.
4. ```ssh pi@pi0wX```
5. ```sudo docker swarm join --token **Aqui el token** 192.168.ipMANAGER:2377```
6. Repetir los pasos __4__ y __5__ con cada nodo o utilizar un multiplexor de terminal.
### Notas
- Es muy aconsejable tener al menos 2 managers. En caso de que haya que reiniciar el unico manager o se caiga, el cluster se detendría. Aunque dado que en mi caso de desarrollo tanto la base de datos como el servicio princpal se alojan solo en una maquina, es un riesgo que estoy dispuesto a correr por simplicidad.

## Testing de Swarm
```bash
sudo docker service create \
    --name viz \
    --publish 8080:8080/tcp \
    --constraint node.role==manager \
    --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
    alexellis2/visualizer-arm:latest
```
Un visualizador de servicios debería haberse creado en la ipManager:8080. Esto demuestra que el cluster esta corriendo correctamente y se pueden lanzar los servicios de nuestro cluster.

## Claves de API para los nodos
Aun falta por automatizar este paso, pero por el momento, la solucion que tengo es agregar las claves de API a mano con un multiplexor de terminales. Es rapido.
SSH en cada nodo.

El programa recurre a varias variables de entorno para funcionar, y aqui las definimos. Hasta que sepa pasarlas por Docker, es lo que hay.

```bash
sudo nano ~/.profile
```

```bash
export TEST_BINANCE_API_KEY="TEST_API_KEY HERE"
export TEST_BINANCE_API_SEC="TEST_API_SECRET HERE"
export BINANCE_API_KEY="REAL_API_KEY"
export BINANCE_API_SEC="REAL_API_SECRET"
```

## Configuración de Base de Datos
Por defecto, el servidor SQL solo funciona en localhost y necesitamos hacerlo accesible desde cualquier parte del cluster. Para eso, modificamos un archivo de configuración de mariaDB de la siguiente manera:
 ```bash
 sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
 ```
 Buscamos la línea bind-address y cambiamos la ip actual (loopback) por 0.0.0.0
 
A falta de que se automatize la creación de una plantilla de base de datos, se deberán ejecutar las siguientes instrucciones.

sudo mariadb
GRANT ALL ON *.binance

