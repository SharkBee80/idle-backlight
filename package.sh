#!/bin/bash

# 获取脚本所在的绝对路径目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# 获取脚本的绝对路径本身（如果需要的话）
SCRIPT_PATH="$(readlink -f "$0")"

# 检查当前用户是否为 root
if [ "$EUID" -ne 0 ]; then
	echo "此脚本需要管理员权限，正在尝试切换..."
	# 自动使用 sudo 重新运行当前脚本，使用绝对路径确保重新执行时路径准确
	exec sudo "$SCRIPT_PATH" "$@"
else
	echo "当前已成功以 root 权限运行！"
fi

# 切换到脚本所在的绝对路径目录，确保后续的相对路径（如 .venv, main.py）都能正确找到
cd "$SCRIPT_DIR" || {
	echo "无法进入脚本目录 $SCRIPT_DIR"
	exit 1
}

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
systemctl stop idle-backlight.service
cp dist/idle-backlight /usr/local/bin/idle-backlight
systemctl start idle-backlight.service
echo "done"

# 修复了 read 命令的语法问题
read -rp "按 Enter 键退出..."
