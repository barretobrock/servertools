# MQTT - Local Setup & Maintenance

## Topics
I'll try to remember to lits all the MQTT topics to subscribe to here:
 - sensors/+/temp               # General temperature sensors at various locations
 - sensors/machines/+/temp      # Temps of all machines 
 - sensors/machines/+/uptime    # Uptime of all machines
 - sensors/machines/+/status
 - sensors/cameras/+/status     # Status of all cameras
 
## Actions
 - Subscribing to a topic
    `mosquitto_sub -t <topic>`
 - Publishing to a topic
    `mosquitto_pub -h <host> -m <message> -t <topic> [-d]` 
