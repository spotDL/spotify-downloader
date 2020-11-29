import unittest
import os
import sys
from ..spotDlApp import SpotDlApp
from ..search.spotifyClient import SpotifyClient
from mock import patch
import mock


class TestStringMethods(unittest.TestCase):

    def test_given_clientId_arg_when_not_given_clientSecret_exit_with_error(self):
        with self.assertRaises(SystemExit) as captor:
            with patch('spotdl.search.spotifyClient.SpotifyClient') as mock:
                with patch('spotdl.download.downloader.DownloadManager') as dlMock:
                    app = SpotDlApp()
                    app.runSpotDl(['--clientId', 'someid', 'spotifyurl'], mock, dlMock)
                    self.assertEqual(cm.exception.code, 1)


    def test_given_clientSecret_arg_when_not_given_clientId_exit_with_error(self):
        with self.assertRaises(SystemExit) as captor:
            with patch('spotdl.search.spotifyClient.SpotifyClient') as mock:
                with patch('spotdl.download.downloader.DownloadManager') as dlMock:
                    app = SpotDlApp()
                    app.runSpotDl(['--clientSecret', 'someSecret', 'spotifyurl'], mock, dlMock)
                    self.assertEqual(cm.exception.code, 1)

    def test_given_given_help_arg_exit_with_normal_code(self):
        with self.assertRaises(SystemExit) as captor:
            with patch('spotdl.search.spotifyClient.SpotifyClient') as mock:
                with patch('spotdl.download.downloader.DownloadManager') as dlMock:
                    app = SpotDlApp()
                    app.runSpotDl(['--help'], mock, dlMock)
                    self.assertEqual(cm.exception.code, 0)

    def test_given_given_h_arg_exit_with_normal_code(self):
        with self.assertRaises(SystemExit) as captor:
            with patch('spotdl.search.spotifyClient.SpotifyClient') as mock:
                with patch('spotdl.download.downloader.DownloadManager') as dlMock:
                    app = SpotDlApp()
                    app.runSpotDl(['--h'], mock, dlMock)
                    self.assertEqual(cm.exception.code, 0)

    def test_given_clientId_and_clientSecret_args_provided_when_app_started_init_client_with_provided_values(self):
        with patch('spotdl.search.spotifyClient.SpotifyClient') as initMock:
            with patch('spotdl.download.downloader.DownloadManager') as dlMock:
                app = SpotDlApp()
                clientId = 'someClientId'
                clientSecret = 'someClientSecret'
                app.runSpotDl(['--clientId', clientId, '--clientSecret', clientSecret, 'spotifyurl'], initMock, dlMock)
                initMock.initialize.assert_called()
                initMock.initialize.assert_called_with(clientId=clientId, clientSecret=clientSecret)

    def test_given_clientId_and_clientSecret_args_NOT_provided_when_app_started_init_client_with_default_values(self):
        with patch('spotdl.search.spotifyClient.SpotifyClient') as initMock:
            with patch('spotdl.download.downloader.DownloadManager') as dlMock:
                app = SpotDlApp()
                clientId = SpotDlApp.default_client_id
                clientSecret = SpotDlApp.default_client_secret
                app.runSpotDl(['--clientId', clientId, '--clientSecret', clientSecret, 'spotifyurl'], initMock, dlMock)
                initMock.initialize.assert_called()
                initMock.initialize.assert_called_with(clientId=clientId, clientSecret=clientSecret)

if __name__ == '__main__':
    unittest.main()