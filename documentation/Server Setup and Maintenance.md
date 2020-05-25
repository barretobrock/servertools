# Server Setup and Maintenance

## SETUP
 
### Ubuntu install (18.04 was ultimately used)
 - Wipe USB flashdrive
   `sudo dd if=/dev/zero of=/dev/sdx bs=1M status=progress`
 - Load Linux image onto USB flashdrive
    `sudo dd if=~/Documents/distros/ubuntu_img.img of=/dev/sdx conv=fsync status=progress bs=4M`
 - After loading, insert USB into target computer, boot it up while pressing F12
 - Install as instructed
### Pihole install
 - Follow instructions [here](http://www.ubuntuboss.com/how-to-install-pihole-on-ubuntu-18-04/)
 - from CLI: `pihole disable`
 - If copying from a previous machine, copy these files from `etc/pihole/`:
  - whitelist.txt
  - blacklist.txt
  - adlists.list
 - `pihole enable`
### MySQLDB install
 - `sudo apt install mysql-server`
 - For user creation steps, follow instructions [here](https://www.digitalocean.com/community/tutorials/how-to-create-a-new-user-and-grant-permissions-in-mysql)
### Grafana install
 - Follow instructions [here](http://docs.grafana.org/installation/debian/)
### Openhab install
 - Install Java 8 (9 / 10 don't work with OH yet)
    `sudo apt install openjdk-8-jdk`
 - Follow instructions [here](https://www.openhab.org/docs/installation/linux.html)

    
