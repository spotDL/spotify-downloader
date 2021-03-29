import webview
import secrets
import platform
import urllib
import asyncio
import threading
import http.client
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from time import sleep
from spotipy.oauth2 import SpotifyOAuth
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
        def do_GET(self):
            if self.path.startswith("/callback?"):
                try:
                    parsedRequest = urllib.parse.parse_qs(self.path[10:], strict_parsing=True, errors="strict")
                    if parsedRequest.get("error"):
                        print(f'Auth Error: {parsedRequest.get("error")[0]}')
                        self.send_response(500)
                    else:
                        self.send_response(200,
                            '<html><head></head><body></body></html>'
                        )
                        output['keepServing'] = False
                        output['data'] = (parsedRequest.get("code")[0],parsedRequest.get("state")[0])
                        
                except:
                    print("Malformed request received by http server.")
            else:
                self.send_error(400)
            return None

    server = HTTPServer(("127.0.0.1", 8080), CallbackHandler)
    while output.get("keepServing"):
        server.handle_request()
        sleep(0.1)
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
        webview.start()
    
    

def get_user_auth_token(client_id:str, client_secret:str)->str:
    '''
        This function prompts the user for login, then returns a Spotipy Credential Manager
    '''
    # Creates state
    state = secrets.token_hex(32)
    
    # Create login URL
    loginURL = (
        f'https://accounts.spotify.com/authorize?'
        f'client_id={client_id}&'
        f'response_type=code&'
        f'redirect_uri=http%3A%2F%2F127.0.0.1%3A8080%2Fcallback&'
        f'state={state}&'
        f'scope=playlist-read-private%20playlist-read-collaborative%20user-library-read&'
        f'show_dialog=true'
    )

    # Variables where the result will be stored
    code = None
    returnedState = None
    
    # Two threads need to run side by side.
    # - A Webview window
    # - An http server to capture the OAuth callback
    with ProcessPoolExecutor(max_workers=2) as pool:
        webviewFuture = pool.submit(_run_webview,loginURL)
        httpFuture = pool.submit(_run_http_server)
        results = wait([webviewFuture,httpFuture],return_when=FIRST_COMPLETED)
        finishedFuture = results.done.pop()
        if finishedFuture == webviewFuture:
            raise Exception("User Rejected Authorization")
        else:
            returnedTuple = httpFuture.result()
            code = returnedTuple[0]
            returnedState = returnedTuple[1]

    
    if returnedState != state:
        raise Exception("Detected attempt at CSRF")
    
    print(code)
    raise NotImplementedError("Coming Soon!")