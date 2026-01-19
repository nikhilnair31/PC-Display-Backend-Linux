# E-Ink Dashboard

## To-Do
- Add default image on pi when server fails
- Add multi layout dropdown
- Add rules for layout (time/?)
- Add cell rotation
- Add multi select and edit
- Add bold/italic fonts
- Add more?

## Done
- Added printer status
- Improve styling
- Fix labeled image faces
- Check why GPU temp is 0
- Improve font size and boldness

## Pi
### Setup
- Run this `git clone https://github.com/waveshareteam/e-Paper.git` at root
- Run `sudo pip3 install --break-system-package python-dotenv requests`
- No need to use virtual env here

### Service
- Run these when updating the service
    - `sudo systemctl daemon-reload`
    - `sudo systemctl enable refresh_dashboard.service`
    - `sudo systemctl disable refresh_dashboard.service`
    - `sudo systemctl start refresh_dashboard.service`
    - `sudo systemctl stop refresh_dashboard.service`
    - `sudo systemctl restart refresh_dashboard.service`
    - `sudo systemctl status refresh_dashboard.service`
    - `journalctl -u refresh_dashboard -f`
- Might need to run `sudo pkill -9 -f python` since GPIO busy error comes up at times

### Files
- Run the command below to copy a file from the PC to the Pi
`scp <C:\Users\nikna\Downloads\Helmet-Regular.ttf> nikhil@raspberrypi:/home/nikhil/`

### Script
- The script on the pi just reads the image from the server

## Server
### Setup
#### Firewall
- Run `sudo ufw enable`
- Check if firewall is active and enabled on system startup
- If yes then run `sudo ufw allow 5001/tc`
- Run `sudo ufw status`
- Check if it has `5001/tcp ALLOW Anywhere`

#### Power
- Run `iwconfig`
- If Power Management: on then proceed else you're good
- Find/Create `sudo nano /etc/NetworkManager/conf.d/wifi-powersave.conf`
- Write this in it
```
    [connecction]
    wifi.powersave = 2
```
- Run `sudo systemctl restart NetworkManager`
- Run `iwconfig` and check for Power Management: on again

### Service
- Run these when updating the service
    - `sudo systemctl daemon-reload`
    - `sudo systemctl enable dashboard.service`
    - `sudo systemctl disable dashboard.service`
    - `sudo systemctl start dashboard.service`
    - `sudo systemctl stop dashboard.service`
    - `sudo systemctl restart dashboard.service`
    - `sudo systemctl status dashboard.service`
    - `journalctl -u dashboard -f`
- Environment in the service is that to ensure `nvidia-smi` works fine for GPU temp to show correctly
- ExecStart has that at the start for the virtual env reference

### Script
- Have the keys in the `.env` file
- Visit `http://192.168.1.173:5001/canvas` and create the layout you want
- Ensure layout is saved

## Other
- Use https://icons8.com/icons/ for icons