while sleep 10 ;
do
    sudo ./GenerateConfigs.py&&
    sudo /etc/init.d/isc-dhcp-server restart ;
done
