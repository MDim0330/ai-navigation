#!/bin/bash
echo "Configuring Velodyne..."
./velodyne_setup.sh
echo "Setting up display"
xinput map-to-output 19 HDMI-0
wait
sleep 2
echo "Launching Navigation Code..."
gnome-terminal --tab -e 'sh -c "roslaunch cart_control navigation.launch; exec bash"'
sleep 2
echo "Starting local server..."
gnome-terminal --tab -e 'sh -c "cd ~; cd Desktop/jakart-local-server; npm start; exec bash"'

