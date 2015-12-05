#!/bin/bash
source /home/ubuntu/.bashrc
ps -aux | grep "python run_hill.py" | awk '{print $2}' | xargs kill -9
