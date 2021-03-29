import webview
import secrets
import platform
import urllib
import threading
import requests
import base64
import time
from concurrent.futures import ProcessPoolExecutor, wait
from time import sleep
from spotipy.oauth2 import SpotifyAuthBase
from http.server import BaseHTTPRequestHandler, HTTPServer 

def _run_http_server()->(str,str):
    '''
        This function runs an HTTP server until a provided future resolves
    '''
    output = {
        "keepServing": True,
        "data": None
    }
    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return
        def do_GET(self):
            if self.path.startswith("/callback?"):
                try:
                    parsedRequest = urllib.parse.parse_qs(self.path[10:], strict_parsing=True, errors="strict")
                    if parsedRequest.get("error"):
                        print(f'Auth Error: {parsedRequest.get("error")[0]}')
                        self.send_response(500)
                    else:
                        self.send_response(201)
                        output['keepServing'] = False
                        output['data'] = (parsedRequest.get("code")[0],parsedRequest.get("state")[0])
                        
                except:
                    print("Malformed request received by http server.")
            elif self.path.startswith("/killServer"):
                output['keepServing'] = False
                self.send_response(201)
            else:
                self.send_error(400)
            return None

    server = HTTPServer(("127.0.0.1", 8080), CallbackHandler)
    while output.get("keepServing"):
        server.handle_request()
    server.server_close()
    return output.get("data")

def _run_webview(loginURL:str):
    
    # Create login window
    loginWindow = webview.create_window(
        title='Spotify Login',
        url=loginURL
    )
    def kill_login_window():
        if loginWindow.get_current_url().startswith("http://127.0.0.1:8080/callback?"):
            loginWindow.destroy()
    loginWindow.loaded += kill_login_window
    
    # Start webview with correct backend
    currPlatform = platform.system()
    if currPlatform == "Windows":
        webview.start(gui="cef")
    elif currPlatform == "Linux":
        webview.start(gui="qt")
    elif currPlatform == "Darwin":
        webview.start()
    else:
        print("Could not determine platform. Attempting to start Login Window.")
    requests.get("http://127.0.0.1:8080/killServer")

def _refresh_access_token(inst):
    print("Refreshing Access Token...")
    while(inst._active):
        timeToSleep = inst._expiryTime - time.time()
        if(timeToSleep >= 60):
            time.sleep(timeToSleep)
        inst._accessTokenLock.acquire()

        authString = base64.b64encode(bytes(f"{inst._clientId}:{inst._clientSecret}",'utf-8')).decode('utf-8')
        
        newToken = requests.post("https://accounts.spotify.com/api/token",{
            "grant_type": "refresh_token",
            "refresh_token": inst._refreshToken
        },headers={
            "Authorization": f"Basic {authString}"
        }).json()

        if newToken.get("error"):
            raise Exception(f"Could not refresh Access Token: {newToken.get('error')}")

        inst._currAccessToken = newToken.get("access_token")
        inst._expiryTime = time.time() + int(newToken.get("expires_in")) - 60
        inst._accessTokenLock.release()


class SpotifyUserAuth(SpotifyAuthBase):
    _active = True
    _scope = "playlist-read-private playlist-read-collaborative user-library-read"
    _clientId = None
    _clientSecret = None
    _currAccessToken = None
    _accessTokenLock = None
    _refreshToken = None
    _expiryTime = None
    _refreshTokenThread = None

    def __init__(self,client_id:str, client_secret:str):
        '''
            The init function for SpotifyUserAuth
            Meant to be initialized only once
            Errors ahoy if you dare otherwise
        '''
        self._clientId = client_id
        self._clientSecret = client_secret

        redirect_uri = 'http://127.0.0.1:8080/callback'

        # Creates state
        state = secrets.token_hex(32)
        
        # Create login URL
        loginURL = (
            f'https://accounts.spotify.com/authorize?'
            f'client_id={client_id}&'
            f'response_type=code&'
            f'redirect_uri={urllib.parse.quote(redirect_uri)}&'
            f'state={state}&'
            f'scope={urllib.parse.quote(self._scope)}&'
            f'show_dialog=false'
        )
        
        # Two threads need to run side by side.
        # - A Webview window
        # - An http server to capture the OAuth callback
        # Sadly, webview requires to be run as a separate process,
        # So I had to use ProcessPoolExecutor instead of ThreadPoolExecutor
        with ProcessPoolExecutor(max_workers=2) as pool:
            webviewFuture = pool.submit(_run_webview,loginURL)
            httpFuture = pool.submit(_run_http_server)
            wait([webviewFuture,httpFuture])
            if not httpFuture.result():
                raise Exception("User Refused Authentication")
        
        returnedCode = httpFuture.result()[0]
        returnedState = httpFuture.result()[1]

        if returnedState != state:
            raise Exception("Detected attempt at CSRF")
        
        authString = base64.b64encode(bytes(f"{client_id}:{client_secret}",'utf-8')).decode('utf-8')
        tokens = requests.post('https://accounts.spotify.com/api/token',{
            'grant_type': 'authorization_code',
            'code': returnedCode,
            'redirect_uri': 'http://127.0.0.1:8080/callback'
        },headers={
            'Authorization': f'Basic {authString}'
        }).json()

        if tokens.get("error"):
            raise Exception(f'Authorization Error: {tokens.get("error")}')
        
        self._currAccessToken = tokens.get("access_token")
        self._refreshToken = tokens.get("refresh_token")
        self._expiryTime = time.time() + int(tokens.get("expires_in")) - 60
        self._accessTokenLock = threading.Lock()

        threading.Thread(name="_refresh_access_token",target=_refresh_access_token,args=(self,)).start()
    
    def __del__(self):
        self._active = False

    def get_access_token(self, as_dict=True):
        self._accessTokenLock.acquire()
        currToken = self._currAccessToken
        self._accessTokenLock.release()
        if as_dict:
            return {
                "access_token": currToken,
                "refresh_token": self._refreshToken,
                "expires_in": self._expiryTime - time.time(),
                "token_type": "Bearer",
                "scope": self._scope
            }
        else:
            return currToken