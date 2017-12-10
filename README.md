# Robot Vision
A wrapper for GRIP running on a Raspberry Pi 3


## Prerequisites:
1. A Raspberry Pi 3
2. A USB Camera
3. An OpenCV installation (if not present, follow [this guide](https://www.pyimagesearch.com/2017/09/04/raspbian-stretch-install-opencv-3-python-on-your-raspberry-pi/))
4. A MJPG-Streamer installation
   
## Installation:
1. Clone the repository.
2. `cd` into the cloned repository.
3. Edit `main.py` so that `URL` and `TEAM_NUMBER` correspond to your Raspberry Pi stream and your team number.
4. Run `sudo pip3 install -r requirements.txt`
5. To start the program, run `python main.py`
