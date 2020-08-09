.. include:: badges.rst

Installation
************

.. NOTE::
    Only Python 3.6+ is supported. Anything lower is not supported.


Debian-like GNU/Linux & macOS
=============================

You can install the latest release by invoking pip with:

.. CODE::

    $ pip install -U spotdl

.. ATTENTION::
    If you have both Python 2 and 3 installed, the *pip* command
    could invoke an installation for Python 2. To see which Python
    version *pip* refers to, try running:

    .. CODE::

        $ pip -V

    If it turns out that *pip* points to Python 2, try running:

    .. CODE::

        $ pip3 install -U spotdl

    instead.

You'll also need to install FFmpeg for conversion:

- **Debian-like GNU/Linux**

    .. CODE::

        $ sudo apt-get install ffmpeg

- **macOS**

    .. CODE::

        $ brew install ffmpeg --with-libmp3lame --with-libass --with-opus --with-fdk-aac

If FFmpeg does not install correctly in the above step, depending on
your OS, you may have to build it from source.
For more information see `FFmpeg's compilation guide <https://trac.ffmpeg.org/wiki/CompilationGuide>`_.


Windows
=======

Assuming you have Python 3.6 already installed and in PATH.

Open *command-prompt* and run:

.. CODE::

    $ pip install -U spotdl

to install spotdl.

.. ATTENTION::
    If you have both Python 2 and 3 installed, the *pip* command
    could invoke an installation for Python 2. To see which Python
    version *pip* refers to, try running:

    .. CODE::

        $ pip -V

    If it turns out that *pip* points to Python 2, try running:

    .. CODE::

        $ pip3 install -U spotdl

    instead.

You'll also need to download zip file for an `FFmpeg build <https://ffmpeg.zeranoe.com/builds/>`_.
Extract it and then place *ffmpeg.exe* in a directory included in your
PATH variable. Placing *ffmpeg.exe* in *C:\Windows\\System32* usually
works fine.

To confirm whether *ffmpeg.exe* was correctly installed in PATH, from
any arbitrary working directory try executing:

.. CODE::

    $ ffmpeg

If you get a *command-not-found* error, that means something's still off.

.. NOTE::
    In some cases placing *ffmpeg.exe* in *System32* directory doesn't
    work, if this seems to be happening with you then you need to
    manually add the FFmpeg directory to PATH. Refer to
    `this post <https://docs.alfresco.com/4.2/tasks/fot-addpath.html>`_
    or `this video <https://www.youtube.com/watch?v=qjtmgCb8NcE>`_.

Android (Termux)
================

Install Python and FFmpeg:

.. CODE::

    $ pkg update
    $ pkg install python ffmpeg

Then install spotdl with:

.. CODE::

    $ pip install spotdl

Docker Image
============

|hub.docker.com| |hub.docker.com pulls|

We also provide the latest docker image on `DockerHub <https://hub.docker.com/r/ritiek/spotify-downloader>`_.

- Pull (or update) the image with:

    .. CODE::

        $ docker pull ritiek/spotify-downloader

- Run it with:

    .. CODE::

        $ docker run --rm -it -v $(pwd):/music ritiek/spotify-downloader <arguments>

- The container will download music and write tracks in your current working directory.

**Example - Downloading a Playlist:**

.. CODE::

    $ docker run --rm -it -v $(pwd):/music ritiek/spotify-downloader -p https://open.spotify.com/user/nocopyrightsounds/playlist/7sZbq8QGyMnhKPcLJvCUFD
    $ docker run --rm -it -v $(pwd):/music ritiek/spotify-downloader -l ncs-releases.txt

.. IMPORTANT::
    Changing the root directory where the tracks get downloaded to any
    different than the current directory tree with the *-f* argument
    will **NOT** work with Docker containers.


Vagrant Box
===========

`@csimpi <https://github.com/csimpi>`_ has posted very detailed
instructions `here <https://github.com/ritiek/spotify-downloader/issues/293#issuecomment-400155222>`_.
However, they are now a bit-outdated. So, here's the updated bit based
on the original instructions:

    **Installing Virtualbox and Vagrant**

    You will need Vagrant from http://vagrantup.com, and virtualbox from https://www.virtualbox.org/.

    Setting up Vagrant virtual machine
    Make an empty folder, this folder will contain your vagrant machine.
    Step into the folder and run the following commands:

    .. CODE::

        $ vagrant init ubuntu/trusty64
        $ vagrant up

    Log in to the installed linux instance **(password: vagrant)**

    .. CODE::

        $ vagrant ssh

    Run the following commands:

    .. CODE::

        $ sudo apt-get update
        $ sudo apt-get -y upgrade
        $ sudo apt-get install -y python3-pip
        $ sudo apt-get install build-essential libssl-dev libffi-dev python-dev
        $ sudo apt-get install git

        $ cd ~
        $ git clone https://github.com/ritiek/spotify-downloader
        $ cd spotify-downloader
        $ sudo apt-get install ffmpeg
        $ pip3 install .

    You can link your inside download folder to your physical hard
    drive, so you will be able to get your downloaded files directly
    from your main operation system, don't need to be logged in to the
    Vagrant virtual machine, your downloaded files will be there on
    your computer, and the library won't make any footprint in your
    system.

