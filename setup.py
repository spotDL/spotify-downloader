#!/usr/bin/python

import sys
import os

if sys.version_info > (3,0):
	sys.exit("YTMusic requires python 2.")

from setuptools import setup, find_packages

setup(name='YTMusic',
      version='0.1',
      description='Download songs just by entering the song name and artist.',
      author='Ritiek Malhotra',
      author_email='ritiekmalhotra123@gmail.com',
      url='https://www.github.com/Ritiek/YTMusic/',
      scripts=['bin/YTMusic'],
     )
