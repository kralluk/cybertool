# CyberTool
Webová aplikace .. 
Aplikace je tvořena na Linuxové distribuci Kali na architektuře ARM, odzkoušna funkčnost na Ubuntu architektury x86.
## Requirements

- Python3.8+
- Venv
- Docker a Docker Compose  <!--  https://docs.docker.com/engine/install/linux-postinstall -->
- Tshark
- Hping3
- Nmap


## Proces instalace
- 
- Get to /web_app/, create virtual environment and activate it
```
cd DDoS_testbed/web_app/
python3 -m venv ./venv
. venv/bin/activate
```
- Install necessary packages
```
python3 -m pip install -r requirements.txt
```
- Start the app
```
flask run  # If you want the app to be accessible from other devices on the network -> flask run --host=0.0.0.0
```
- App is running on http://localhost:5000 




## Some notes
- It can take a long time to run the application for the first time, the Docker has to pull the necessary images. In the case of the first botnet generation or changing Apache version, the same applies, but once everything is downloaded, there should no longer be a higher delay.

- Default role in Grafana is Viewer, if you want to enable editing log in with username **admin** and password **1234**.
