# MQTT - Local Setup & Maintenance

## Topics
I'll try to remember to lits all the MQTT topics to subscribe to here:
 - sensors/#                    # All sensors, all levels
 - sensors/+/temp               # General temperature sensors at various locations
 - sensors/cameras/+/status     # Status of all cameras
 - sensors/machines/+/temp      # Temps of all machines
 - sensors/machines/+/uptime    # Uptime of all machines
 - sensors/machines/+/status    # Connection status of all machines
 - sensors/net/speed/download   # Download speed
 - sensors/net/speed/upload     # Upload speed
 - sensors/net/speed/ping       # Server ping

## Actions
 - Subscribing to a topic
    `mosquitto_sub -t <topic>`
 - Publishing to a topic
    `mosquitto_pub -h <host> -m <message> -t <topic> [-d]`
