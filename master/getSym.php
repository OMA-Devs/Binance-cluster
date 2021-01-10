<?php
$sym = $_REQUEST["sym"]; 

#$st = 'python3 /var/www/html/Binance-cluster/master/main.py';
$command = escapeshellcmd('python3 /var/www/html/Binance/master/main.py '.$sym);
$output = shell_exec($command);
#$output = "AHLOOOOO";
echo $output;

?>