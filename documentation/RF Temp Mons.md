# RF Temperature Monitor Guide
This will help with setup and troubleshooting of any known problems

Guides followed:
 - [Raspberry Pi RF Temperature Monitor instructable](https://www.instructables.com/id/Raspberry-Pi-RF-Temperature-Monitor/)
 - [Building docs for rtl_433](https://github.com/merbanan/rtl_433/blob/master/docs/BUILDING.md)

## Setup

###Clone the repo
    
`git clone https://github.com/merbanan/rtl_433.git ~/extras/rtl_433/`

Install all the necessary packages on the pi that will serve as the main node for the transmitters.

`sudo apt install libtool libusb-1.0-0-dev librtlsdr-dev rtl-sdr build-essential autoconf cmake pkg-config`
### Install using CMake:
```bash
cd rtl_433/
mkdir build
cd build
cmake ..
make
make install 
```
### Load services
Loads both streaming and collection services. Stream provides a way to receive RF signals into socket 1024. Collect listens to that socket and records data to db via python script.
```bash
sh api/rf_temps/load_rf_stream_service.sh
sh api/rf_temps/load_rf_collect_service.sh
sudo systemctl start rf_stream
sudo systemctl start rf_collect
```
 
## Resources
- This was helpful in trying to understand the parameters: [link](https://triq.org/rtl_433/INTEGRATION.html)
- Actual docs on [rtl_433](https://github.com/merbanan/rtl_433#user-content-running)