#!/usr/bin/bash

# check .venv
if [ ! -d ".venv" ]; then
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
	pip install pyinstaller
else
	source .venv/bin/activate && echo "venv activated"
fi

echo "pyinstaller start"
pyinstaller --onefile --name=idle-backlight main.py
# pyinstaller idle-backlight.spec
echo "pyinstaller done"

echo "copying to /usr/local/bin"
sudo systemctl stop idle-backlight.service
sudo cp dist/idle-backlight /usr/local/bin/idle-backlight
sudo systemctl start idle-backlight.service
echo "done"
