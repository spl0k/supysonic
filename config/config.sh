#!/bin/bash

mkdir ~/.supysonic
mkdir ~/.supysonic/cache

sudo apt-get install python-pip python-imaging python-simplejson
sudo pip install flask
cp supysonic.conf ~/.supysonic
