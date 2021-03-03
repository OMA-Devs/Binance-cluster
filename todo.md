# To Do

## Campo Real/Testing en los trades para combinar trades de prueba y reales en un mismo nodo

Los trades reales se pueden ejecutar en turno, y el resto del tiempo se pueden seguir simulando para obtener más datos y modificar los valores del algoritmo. Para implementar esta idea hay que modificar las siguientes estructuras.

### Pasos de implementación.

- [x] ```client.py```, donde se centra el grueso de las modificaciones.
    - [x] clase ```AT```. Se tiene que añadir una variable, "SIMULADO". que bifurque la accion de ```openTrade``` en real(dentro del turno) y test(fuera de) DEBUG cumple una funcion similar, pero no es lo que necesito modificar. Se queda, cualquier implementación tiene que respetar el funcioamiento de DEBUG.
		1. __Comentario__: No ha sido necesario modificar la instanciacion de AT. Simplemente he creado una global llamada shift. 
	- [x] ```putTrading``` y ```putTraded``` necesitaran modificaciones en los argumentos que forman el query de las peticiones al servidor.
	- [x] ```monitor``` Necesita un argumento más. "SIMULADO", booleano. Modificamos la funcion para que tenga en cuenta eso a la hora de generar la llamada a mercado. Es igal que en AT.
	- [x] El bucle principal deberá modificarse para que la variable "SIMULATED" se determine dependiendo de si esta en turno o no. 
- [x] ```binance.db```. Se tiene que añadir un campo a la base de datos. En traded y trading. ```real```, por conveniencia con las variables anteriores.
    - [x] Quizá convendría importar las bases de test en excel y añadir ese campo de una sentada. Eso las haría compatibles con los siguientes hooks con django.
	1. __Comentario__: Se han añadido 3 campos adicionales a la tabla symbols para una funcionalidad posterior. El error de sqlBrowser se solventa exportando a csv, modificando con excel y reimportando. Como la seda y comodísimo.
- [ ] ```dbOPS.py```. Otra modificación bastante profunda. Quizá podría pasar sin añadir mas que el campo añadido a las queries sql, pero creo que a largo plazo saldrá a cuenta añadir versiones/bifurcaciones de los metodos para la obtención de datos. Así, todos los trades reales y test podrán ser recuperados en una sola llamada y no habrá que repetir procesamiento posterior a la recuperacion de los datos.
    - [x] getTrading. __Comentario__: Se comenta la funcion entera. Aparentemente esta huerfana, sustituida por TRADINGdict.
	- [x] getTRADINGdict. __Comentario__: Muy sencillo!!!
	- [x] getTRADINGsingle
	- [x] getTRADED. __Comentario__: Se comenta la funcion entera. Aparentemente esta huerfana, sustituioda por TRADEDdict.
	- [x] getTRADEDdict
	- [x] tradeEND
	- [x] tradeSTART
	- [x] removeTrade
	1. __Comentario__: Se modifica la funcion ```updateSymbols``` y ```getSymbols``` para el uso posterior de los campos añadidos en la tabla symbols.
	2. __Comentario__: Muy seguramente, el argumento shift duplicado en casi todas las partes de la definicion de la clase podria ser un atributo de la clase.
	3. __Comentario__: Efectivamente. He podido introducirlo como un argumento de instanciacion y el codigo queda increiblemente mas limpio.
- [x] Django. ```data.views``` necesitará el rework correspondiente. ```display.views``` puede aprovecharse de nuevas caracteristicas.
	1. __Comentario__: Muy facil de modificar tras darme cuenta de que "shift" podía ser un argumento de la instanciación.

## Horarios dinámicos de trading.

Ahora mismo ya esta implementada una funcion horaria en ```client.py``` pero esta se ejecuta durante un periodo de tiempo estipulado en el archivo de configuración y nada mas. Se pretende que el cliente obtenga los datos de la base de datos y determine los horarios de trading más efectivos, aunque estos se sucedan en horas salteadas.
