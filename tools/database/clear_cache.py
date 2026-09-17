#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick script to clear browser cache by adding version parameter to mobile.html
"""
import os
import time

# Add timestamp to force browser reload
timestamp = str(int(time.time()))
print(f"Cache buster timestamp: {timestamp}")
print(f"\nTarayıcıda şu URL'yi açın:")
print(f"http://85.117.239.60:8000/mobile.html?v={timestamp}")
print(f"\nVeya Ctrl+Shift+R (Hard Refresh) yapın!")
