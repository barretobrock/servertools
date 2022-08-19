# Server Setup and Maintenance

## SETUP

### Xubuntu install (20.04)
 - Wipe USB flashdrive
   `sudo dd if=/dev/zero of=/dev/sdx bs=1M status=progress`
 - Load image onto USB flashdrive
    `sudo dd if=~/Documents/distros/ubuntu_img.img of=/dev/sdx conv=fsync status=progress bs=4M`
 - After loading, insert USB into target computer, boot it up while pressing F12
 - Install as instructed

### Setup SSH
```bash
sudo apt update && sudo apt install openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh
# Open up SSH port
sudo ufw allow ssh
sudo ufw enable
sudo ufw status
```
### Use Bash instead of Dash
```bash
sudo dpkg-reconfigure dash
```
### Change BIOS Power settings
F12 during bootup, find BIOS menu and head to power settings
Change to boot back up after power failure

### Pihole install
```bash
sudo apt install curl
curl -sSL https://install.pi-hole.net | bash
```
Make changes to OpenWRT ([instructions](https://www.reddit.com/r/pihole/comments/av1qd4/setting_up_pihole_on_openwrt/))

Confirm working with `dig`:
```bash
dig google.com
```

### Nginx install
```bash
sudo apt install nginx
```

### Influxdb install
```bash
wget -qO- https://repos.influxdata.com/influxdb.key | sudo apt-key add -
source /etc/lsb-release
echo "deb https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
sudo apt update && sudo apt install influxdb
sudo service influxdb start
```
### Grafana install
Follow instructions [here](https://grafana.com/docs/grafana/latest/installation/)
```bash
sudo apt-get install -y apt-transport-https
sudo apt-get install -y software-properties-common wget
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install grafana
sudo systemctl daemon-reload
sudo systemctl start grafana-server
sudo systemctl status grafana-server
sudo systemctl enable grafana-server.service
```
Enable [anonymous authentication](https://grafana.com/docs/grafana/latest/auth/overview/#anonymous-authentication) (uncomment all areas in the section)
```bash
sudo nano /etc/grafana/grafana.ini
```

### Crons/Env Setup
Install dependencies
```bash
sudo apt install build-essential git python3-pip python3-dev python3-venv python3-pandas chromium-chromedriver
```

Make directories/environments
```bash
cd ~ && mkdir data keys logs extras venvs
cd ~/venvs && python3 -m venv stools
```
Install repos & requirements
```bash
cd extras
git clone https://github.com/barretobrock/servertools.git
git clone https://github.com/barretobrock/py-package-manager.git
cd servertools && sh update_script.sh
```
Load keys from backup location
```bash
scp user@backup:/path/to/keys/* ~/keys/
```
Setup HA API service
```
sh api/hosts/load_hosts_api.sh
sh api/homeauto/load_homeauto_api.sh
sudo systemctl start hosts_api.service
sudo systemctl status hosts_api.service
sudo systemctl start homeauto_api.service
sudo systemctl status homeauto_api.service
```


### MQTT install
#### Server-side
 - Install broker
    `sudo apt install mosquitto mosquitto-clients`
 - Confirm that port 1883 is open & listening
    `netstat -at`
    (look for *:1883 & [::]:1883)
 - Stopping/starting service
    `sudo service mosquitto <start|stop>`
#### Client-side
 - Install client
    `sudo apt install mosquitto-clients`
