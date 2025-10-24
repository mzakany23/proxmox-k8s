#!/bin/sh

# Initialize /data/apps.json if it doesn't exist or is empty
if [ ! -f /data/apps.json ] || [ ! -s /data/apps.json ]; then
    echo "Initializing /data/apps.json from image..."
    cp /root/apps.json /data/apps.json
fi

# Start the app
exec ./app-registry
