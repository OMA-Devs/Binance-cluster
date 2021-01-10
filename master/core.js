/**
	 * Llamada generica a archivos php del servidor. Es lo más flexible posible para
	 * ser utilizada en los maximos sitios posibles.
	 * @param {Array} keyARR Contiene las KEYS para generar el query HTTP
	 * @param {Array} valARR Contiene los valores para generar el query HTTP
	 * @param {String} fileTARGET Archivo php de destino en el servidor
	 * @param {String} divTARGET ID del objetivo. Si se entrega una cadena vacía, la
	 * respuesta se dará en un alert, y si no se modificará el elemento entregado.
	 */
function genericCall(keyARR, valARR, fileTARGET, divTARGET){
	var xhttp = new XMLHttpRequest();
	xhttp.onreadystatechange = function() {
	if (this.readyState == 4 && this.status == 200) {
			if (divTARGET == ""){
				console.log(this.responseText)
				alert(this.responseText)
			}else{
				var view = document.getElementById(divTARGET);
				view.innerHTML = ""
				view.innerHTML = this.responseText
			}
		}
	};
	var query = fileTARGET+"?"
	for (var i = 0; i<keyARR.length; i++){
		if (i == keyARR.length-1){
			query += keyARR[i]+"="+valARR[i]
		}else{
			query += keyARR[i]+"="+valARR[i]+"&"
		}
	}
	console.log(query)
	xhttp.open("GET", query, true);
	xhttp.send();
}