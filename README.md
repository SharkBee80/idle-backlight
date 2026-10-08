## what

a script to automatically lower the backlight when the user is `inactive` in `multi-user.target` but not in graphical.target

### platform

- Linux

### _dev environment_

- Python 3.13.5
- Linux 6.12.111+deb13-amd64
- Systemd

## how

1. [release](../../releases) or [dist](/dist) or **`build from source`**

```bash
pip install -r requirements.txt
pip install pyinstaller
```

```bash
pyinstaller --onefile --name=idle-backlight main.py
# pyinstaller idle-backlight.spec
```

2. copy the application to `/usr/local/bin/idle-backlight`

```bash
sudo cp dist/idle-backlight /usr/local/bin/idle-backlight
```

3. create a systemd file

```bash
sudo nano /etc/systemd/system/idle-backlight.service
# or
# sudo nano /usr/lib/systemd/system/idle-backlight.service
```

```ini
[Unit]
Description=Automatic backlight control on input inactivity
After=systemd-udev-settle.service
Wants=systemd-udev-settle.service

[Service]
Type=simple

ExecStart=/usr/local/bin/idle-backlight

Restart=always
RestartSec=3

# This service needs access to /dev/input/event*
User=root

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable idle-backlight.service
sudo systemctl start idle-backlight.service
```

## uninstall

```bash
sudo systemctl stop idle-backlight.service
sudo systemctl disable idle-backlight.service
sudo systemctl daemon-reload
sudo rm /usr/local/bin/idle-backlight
sudo rm /etc/systemd/system/idle-backlight.service
```

## update

```bash
sudo systemctl stop idle-backlight.service
sudo cp dist/idle-backlight /usr/local/bin/idle-backlight
sudo systemctl start idle-backlight.service
```

## todo

- [ ] add a way to set the config

## license

[MIT](LICENSE)
