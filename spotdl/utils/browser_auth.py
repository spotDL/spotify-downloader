"""
Browser-based Spotify authentication using OAuth flow.
This eliminates the need for users to create Spotify Developer Apps.
Based on spotify_to_ytmusic approach by linsomniac.
"""

import codecs
import http.client
import http.server
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import logging
from typing import Optional

__all__ = ["BrowserSpotifyAuth", "get_spotify_token"]

logger = logging.getLogger(__name__)


class BrowserSpotifyAuth:
    """
    Spotify authentication using browser OAuth flow with a public client ID.
    No need for users to create Spotify Developer accounts!
    """
    
    # Public client ID from spotify_to_ytmusic project
    # This is a publicly known client ID that works for everyone
    PUBLIC_CLIENT_ID = "5c098bcc800e45d49e476265bc9b6934"
    
    BASE_URL = "https://api.spotify.com/v1/"
    _SERVER_PORT = 43019
    
    def __init__(self, access_token: str):
        """Initialize with an access token."""
        self.access_token = access_token
        self._auth = access_token
        
    @classmethod
    def authorize(
        cls, 
        scope: str = "playlist-read-private playlist-read-collaborative user-library-read",
        client_id: Optional[str] = None
    ) -> "BrowserSpotifyAuth":
        """
        Authorize using browser OAuth flow.
        
        ### Arguments
        - scope: OAuth scope permissions
        - client_id: Optional custom client ID (uses public one by default)
        
        ### Returns
        - BrowserSpotifyAuth instance with access token
        """
        if client_id is None:
            client_id = cls.PUBLIC_CLIENT_ID
            
        redirect_uri = f"http://127.0.0.1:{cls._SERVER_PORT}/redirect"
        auth_url = cls._construct_auth_url(client_id, scope, redirect_uri)
        
        print("=" * 60)
        print("SPOTIFY BROWSER AUTHENTICATION")
        print("=" * 60)
        print("Opening your browser for Spotify login...")
        print("If the browser doesn't open automatically, copy this URL:")
        print(f"{auth_url}")
        print("=" * 60)
        
        webbrowser.open(auth_url)
        
        server = cls._AuthorizationServer("127.0.0.1", cls._SERVER_PORT)
        
        try:
            print("Waiting for authorization... (check your browser)")
            while True:
                server.handle_request()
        except cls._Authorization as auth:
            print("✅ Authorization successful!")
            return cls(auth.access_token)
        except KeyboardInterrupt:
            print("\n❌ Authorization cancelled by user")
            raise
            
    @staticmethod
    def _construct_auth_url(client_id: str, scope: str, redirect_uri: str) -> str:
        """Construct the Spotify authorization URL."""
        return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
            "response_type": "token",
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
        })
        
    def get(self, url: str, params: dict = None, tries: int = 3):
        """
        Fetch a resource from Spotify API.
        
        ### Arguments
        - url: API endpoint (relative to BASE_URL or full URL)
        - params: Query parameters
        - tries: Number of retry attempts
        
        ### Returns
        - JSON response data
        """
        if params is None:
            params = {}
            
        url = self._construct_url(url, params)
        
        for attempt in range(tries):
            try:
                req = self._create_request(url)
                return self._read_response(req)
            except urllib.error.HTTPError as e:
                if e.code == 429:  # Rate limited
                    retry_after = int(e.headers.get('Retry-After', 30))
                    logger.warning(f"Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                elif e.code == 401:  # Unauthorized
                    raise Exception("Access token expired or invalid")
                elif attempt == tries - 1:  # Last attempt
                    raise e
                else:
                    time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                if attempt == tries - 1:
                    raise e
                time.sleep(1)
                
        raise Exception(f"Failed to fetch {url} after {tries} attempts")
        
    def _construct_url(self, url: str, params: dict) -> str:
        """Construct full API URL with parameters."""
        if not url.startswith(self.BASE_URL):
            url = self.BASE_URL + url
            
        if params:
            separator = "&" if "?" in url else "?"
            url += separator + urllib.parse.urlencode(params)
            
        return url
        
    def _create_request(self, url: str):
        """Create authenticated HTTP request."""
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {self.access_token}")
        return req
        
    def _read_response(self, req):
        """Read and parse JSON response."""
        with urllib.request.urlopen(req) as res:
            reader = codecs.getreader("utf-8")
            return json.load(reader(res))
            
    def list(self, url: str, params: dict = None) -> list:
        """
        Fetch all items from a paginated endpoint.
        
        ### Arguments
        - url: API endpoint
        - params: Query parameters
        
        ### Returns
        - List of all items across all pages
        """
        if params is None:
            params = {}
            
        items = []
        
        while url:
            response = self.get(url, params)
            items.extend(response.get("items", []))
            url = response.get("next")
            params = {}  # Next URL already includes parameters
            
        return items
        
    class _AuthorizationServer(http.server.HTTPServer):
        """Simple HTTP server to handle OAuth redirect."""
        
        def __init__(self, host: str, port: int):
            super().__init__((host, port), BrowserSpotifyAuth._AuthorizationHandler)
            
        def handle_error(self, request, client_address):
            """Override to suppress _Authorization exception tracebacks."""
            # Get the current exception
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            
            # Only suppress our expected _Authorization exception
            if exc_type is BrowserSpotifyAuth._Authorization:
                # Re-raise it so it can be caught by the authorize method
                raise exc_value
            else:
                # For other exceptions, use default behavior
                super().handle_error(request, client_address)
            
    class _AuthorizationHandler(http.server.BaseHTTPRequestHandler):
        """Handle OAuth redirect and extract access token."""
        
        def do_GET(self):
            """Handle GET request from OAuth redirect."""
            if self.path.startswith("/redirect"):
                self._handle_redirect()
            else:
                self._handle_token()
                
        def _handle_redirect(self):
            """Handle initial redirect from Spotify."""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            # JavaScript to extract token from URL fragment and send it back
            html = '''
            <html>
            <head><title>Spotify Authorization</title></head>
            <body>
                <h2>🎵 Spotify Authorization</h2>
                <p>Processing authorization...</p>
                <script>
                    // Extract access token from URL fragment
                    var params = new URLSearchParams(location.hash.slice(1));
                    var token = params.get('access_token');
                    
                    if (token) {
                        // Send token to server
                        fetch('/token?access_token=' + token)
                            .then(() => {
                                document.body.innerHTML = 
                                    '<h2>Success!</h2>' +
                                    '<p>Authorization complete. You can close this window.</p>';
                                // Auto-close after 3 seconds
                                setTimeout(() => window.close(), 3000);
                            });
                    } else {
                        document.body.innerHTML = 
                            '<h2>Error</h2>' +
                            '<p>No access token received. Please try again.</p>';
                    }
                </script>
            </body>
            </html>
            '''
            self.wfile.write(html.encode())
            
        def _handle_token(self):
            """Handle token extraction request."""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
            
            # Extract access token from URL
            match = re.search(r"access_token=([^&]*)", self.path)
            if match:
                access_token = match.group(1)
                raise BrowserSpotifyAuth._Authorization(access_token)
                
        def log_message(self, format, *args):
            """Suppress server logs."""
            pass
            
    class _Authorization(Exception):
        """Exception to carry access token back from server."""
        
        def __init__(self, access_token: str):
            self.access_token = access_token


def get_spotify_token(use_existing: bool = True) -> str:
    """
    Get a Spotify access token using browser authentication.
    
    ### Arguments
    - use_existing: Whether to try using an existing token (future enhancement)
    
    ### Returns
    - Access token string
    """
    try:
        spotify_auth = BrowserSpotifyAuth.authorize()
        return spotify_auth.access_token
    except KeyboardInterrupt:
        print("\n❌ Authorization cancelled by user")
        raise
    except Exception as e:
        logger.error(f"Failed to get Spotify token: {e}")
        raise


def test_token(token: str) -> bool:
    """
    Test if a Spotify token is valid.
    
    ### Arguments
    - token: Access token to test
    
    ### Returns
    - True if token is valid, False otherwise
    """
    try:
        auth = BrowserSpotifyAuth(token)
        auth.get("me")  # Try to get user profile
        return True
    except:
        return False


if __name__ == "__main__":
    # Test the authentication
    print("Testing Spotify browser authentication...")
    
    try:
        token = get_spotify_token()
        print(f"✅ Got access token: {token[:20]}...")
        
        # Test the token
        auth = BrowserSpotifyAuth(token)
        user = auth.get("me")
        print(f"✅ Authenticated as: {user.get('display_name', 'Unknown')}")
        
        # Test getting playlists
        playlists = auth.list("me/playlists", {"limit": 5})
        print(f"✅ Found {len(playlists)} playlists")
        
        if playlists:
            print("First playlist:", playlists[0].get("name"))
            
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)