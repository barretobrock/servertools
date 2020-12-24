# NGINX Setup 

## Prerequisites
 - Services running
 - .local domains enabled on OpenWRT router

## Resources
 - 

## Installation
```bash 
sudo apt install nginx  
```

## Setup
Make the file for the reverse proxies
```bash
sudo nano /etc/nginx/sites-available/tinyserv.local
```
Add the following
```bash                         
server {
    listen 81;
    listen [::]:81;
    server_name ha.tinyserv.local;
    location / {
        proxy_set_header Host $host;
        proxy_pass http://127.0.0.1:5002;
        proxy_redirect off;
    }
}
```
Link file to sites-enabled
```bash
sudo ln -s /etc/nginx/sites-available/your_domain /etc/nginx/sites-enabled/
```