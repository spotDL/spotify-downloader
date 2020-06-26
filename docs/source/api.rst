API
***

If you recognize any shortcomings while using the API, please report!


API Reference
=============

spotdl.command_line
-------------------

.. autoclass:: spotdl.command_line.core.Spotdl
   :members:

spotdl.track
------------

.. autoclass:: spotdl.track.Track
   :members:

spotdl.metadata_search
----------------------

.. autoclass:: spotdl.metadata_search.MetadataSearch
   :members:

spotdl.metadata
---------------

.. autofunction:: spotdl.metadata.format_string

.. autoclass:: spotdl.metadata.providers.ProviderSpotify
   :members:

.. autoclass:: spotdl.metadata.providers.ProviderYouTube
   :members:

.. autoclass:: spotdl.metadata.providers.YouTubeSearch
   :members:

.. autoclass:: spotdl.metadata.providers.youtube.YouTubeStreams
   :members:

.. autoclass:: spotdl.metadata.embedders.EmbedderDefault
   :members:

spotdl.encode
-------------

.. autoclass:: spotdl.encode.encoders.EncoderFFmpeg
   :members:

spotdl.lyrics
-------------

.. autoclass:: spotdl.lyrics.providers.Genius
   :members:

.. autoclass:: spotdl.lyrics.providers.LyricWikia
   :members:

spotdl.authorize
----------------

.. autoclass:: spotdl.authorize.services.AuthorizeSpotify
   :members:

spotdl.helpers
--------------

.. autoclass:: spotdl.helpers.SpotifyHelpers
   :members:


Abstract Classes
================

spotdl.encode
-------------

.. autoclass:: spotdl.encode.EncoderBase
   :members:

spotdl.metadata
---------------

.. autoclass:: spotdl.metadata.EmbedderBase
   :members:

.. autoclass:: spotdl.metadata.ProviderBase
   :members:

.. autoclass:: spotdl.metadata.StreamsBase
   :members:
