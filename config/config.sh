#!/bin/bash

if [[ ! -d ~/.supysonic && ! -L ~/.supysonic ]] ; then
      echo "Creating ~/.supysonic/"
      mkdir ~/.supysonic
      mkdir ~/.supysonic/cache
fi

sudo apt-get install python-pip python-imaging python-simplejson
sudo pip install flask
cp supysonic.conf ~/.supysonic
