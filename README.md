## what

a script to automatically lower the backlight when the user is inactive

## how

1. copy the script to `/usr/local/bin/idle-backlight.py`

2. create a systemd file

```bash
sudo nano /etc/systemd/system/idle-backlight.service
```

```ini
[Unit]
Description=Automatic backlight control on input inactivity
After=systemd-udev-settle.service
Wants=systemd-udev-settle.service

[Service]
Type=simple

ExecStart=/usr/local/bin/idle-backlight.py

Restart=always
RestartSec=2

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
