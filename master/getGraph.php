<?php
$sym = $_REQUEST["sym"]; 
$command = escapeshellcmd('python3 /var/www/html/Binance/master/graphs.py '.$sym);
$output = shell_exec($command);
#echo $output;
echo file_get_contents("graph.html")
?>