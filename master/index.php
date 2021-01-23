<!doctype html>

<html lang="en">
<head>
  <meta charset="utf-8">

  <title>Trading Management (Alpha)</title>
  <meta name="description" content="Trading Management">
  <meta name="author" content="Oma-Devs">

  <link rel="stylesheet" href="../assets/w3.css">
  <script src="../assets/plotly-latest.min.js"></script>
  <script src="core.js"></script>
</head>

<body class="w3-container">
<div class="w3-container"> 
	<h1 class="w3-center">Trading Management</h1>
</div>
<div class="w3-bar">
	<p class="w3-bar-item w3-button w3-mobile">Trading</p>
	<p class="w3-bar-item w3-button w3-mobile">Traded</p>
	<p class="w3-bar-item w3-button w3-mobile">Section</p>
	<p class="w3-bar-item w3-button w3-mobile">Section</p>
</div>
<h1 class="w3-button" onclick='genericCall(["sym"],["ETH"],"getSym.php","PARES")'>PRUEBA ETH</h1>
<h1 class="w3-button" onclick='genericCall(["sym"],["BNB"],"getSym.php","PARES")'>PRUEBA BNB</h1>
<h1 class="w3-button" onclick='genericCall(["sym"],["BTCEUR"],"getGraph.php","PARES")'>PRUEBA Grafico</h1>
<div id="PARES"></div>
</body>
</html>
