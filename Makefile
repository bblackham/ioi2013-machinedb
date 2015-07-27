all: help

help:
	@echo "IOI 2013 Contestant Heartbeat Service"
	@echo "make install to install, make uninstall to uninstall."
	@echo "make sure the current image version is in /var/contestant_image_version"

install:
	@echo "Installing..."
	sudo mkdir /usr/bin/machinedb
	sudo cp -r static /usr/bin/machinedb/
	sudo cp -r templates /usr/bin/machinedb/
	sudo cp *.py /usr/bin/machinedb/
	sudo cp *.sh /usr/bin/machinedb/
	sudo cp machinedb /etc/init.d/
	sudo chmod +x /usr/bin/machinedb/*.py
	sudo chmod +x /usr/bin/machinedb/*.sh
	sudo chmod +x /etc/init.d/machinedb
	@echo "Done!"
	@echo "Start the service using:"
	@echo "    sudo service machinedb start"
	@echo "Stop the service using:"
	@echo "    sudo service machinedb stop"

uninstall:
	@echo "Uninstalling (make sure service is stopped!)..."
	sudo rm -rf /usr/bin/machinedb
	sudo rm /etc/init.d/machinedb
