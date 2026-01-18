#!/usr/bin/env python3
"""
Flatpak Zotero API Port Forwarding Helper

This script helps expose the Zotero Connector API port from a flatpak Zotero
installation to the host system.

Usage:
    python flatpak_port_forward.py [--install]
    
Options:
    --install    Install the port forwarding systemd service
"""

import os
import sys
import subprocess
import argparse

FLATPAK_ZOTERO_PORT = 23119
HOST_BIND_ADDRESS = "127.0.0.1"

def check_flatpak():
    """Check if running inside flatpak"""
    return os.path.exists("/.flatpak-info")

def get_flatpak_zotero_ip():
    """Get the internal IP of flatpak Zotero"""
    try:
        result = subprocess.run(
            ["flatpak", "info", "org.zotero.Zotero"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return "10.211.05.2"  # Default flatpak network gateway
    except Exception as e:
        print(f"Warning: Could not get flatpak info: {e}")
    return None

def install_port_forwarding():
    """Install systemd service for port forwarding"""
    if not check_flatpak():
        print("This script should be run from INSIDE the flatpak environment")
        print("Or use the alternative: --forward-host flag")
        return False

    service_content = f"""[Unit]
Description=Zotero Connector API Port Forwarding
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:{FLATPAK_ZOTERO_PORT},bind={HOST_BIND_ADDRESS},fork TCP:host.outer.ip:{FLATPAK_ZOTERO_PORT}
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
    
    service_path = "/etc/systemd/system/zotero-port-forward.service"
    
    try:
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", "zotero-port-forward"])
        subprocess.run(["systemctl", "start", "zotero-port-forward"])
        
        print(f"Installed port forwarding service at {service_path}")
        return True
    except Exception as e:
        print(f"Failed to install service: {e}")
        return False

def create_socat_container_script():
    """Create a socat script for use inside flatpak"""
    script_content = f"""#!/bin/bash
# Zotero Connector API Port Forwarding Script
# Run this inside flatpak to forward port {FLATPAK_ZOTERO_PORT} to host

# Install socat if not available
if ! command -v socat &> /dev/null; then
    echo "Installing socat..."
    flatpak install flathub org.freedesktop.Platform.Compat.i386//22.08 || true
fi

echo "Starting Zotero API port forwarding..."
echo "Forwarding flatpak port {FLATPAK_ZOTERO_PORT} to host..."

# Forward port with socat
socat TCP-LISTEN:{FLATPAK_ZOTERO_PORT},bind=127.0.0.1,fork TCP:host.outer.ip:{FLATPAK_ZOTERO_PORT} &

echo "Port forwarding active. Press Ctrl+C to stop."
wait
"""
    
    script_path = os.path.expanduser("~/zotero_port_forward.sh")
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"Created port forwarding script: {script_path}")
    print(f"Run inside flatpak: flatpak run --env=LD_LIBRARY_PATH=/var/run/host/usr/lib/... {script_path}")
    return script_path

def create_zotero_env_script():
    """Create environment setup script for ZotLink"""
    script_content = f"""#!/bin/bash
# Zotero Environment Setup for ZotLink
# Run this script to configure Zotero API access

# Check if Zotero is running
if command -v curl &> /dev/null; then
    if curl -s http://127.0.0.1:{FLATPAK_ZOTERO_PORT}/connector/ping > /dev/null 2>&1; then
        echo "✅ Zotero Connector API is accessible at http://127.0.0.1:{FLATPAK_ZOTERO_PORT}"
        echo "export ZOTERO_API_PORT={FLATPAK_ZOTERO_PORT}"
        export ZOTERO_API_PORT={FLATPAK_ZOTERO_PORT}
    else
        echo "⚠️ Zotero Connector API not accessible at port {FLATPAK_ZOTERO_PORT}"
        echo "Make sure Zotero desktop app is running"
    fi
fi

# For flatpak installations, set this environment variable:
# export ZOTLINK_ZOTERO_ROOT=~/.zotero-zotero
"""
    
    script_path = os.path.expanduser("~/setup_zotero_env.sh")
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    print(f"Created environment setup script: {script_path}")
    return script_path

def main():
    parser = argparse.ArgumentParser(description="Zotero Flatpak Port Forwarding Helper")
    parser.add_argument("--install", action="store_true", help="Install systemd service for port forwarding")
    parser.add_argument("--create-script", action="store_true", help="Create socat port forwarding script")
    parser.add_argument("--setup-env", action="store_true", help="Create environment setup script")
    
    args = parser.parse_args()
    
    print("ZotLink - Zotero Flatpak Configuration Helper")
    print("=" * 50)
    
    if check_flatpak():
        print("Running inside flatpak environment")
        if args.install:
            install_port_forwarding()
        elif args.create_script or not any([args.install, args.setup_env]):
            create_socat_container_script()
    else:
        print("Running on host system")
        print("\nFor flatpak Zotero installations:")
        print("1. Zotero's Connector API runs on port 23119 inside flatpak")
        print("2. To access it from host, you need to:")
        print("   a) Use --socket=x11 --socket=network flags when running flatpak")
        print("   b) Or run Zotero natively (not via flatpak)")
        print("\nRecommended: Install Zotero natively for full API access")
        print("Download: https://www.zotero.org/download/")
        
        if args.setup_env:
            create_zotero_env_script()
        else:
            create_zotero_env_script()
            create_socat_container_script()
    
    print("\n" + "=" * 50)
    print("Configuration complete!")

if __name__ == "__main__":
    main()
