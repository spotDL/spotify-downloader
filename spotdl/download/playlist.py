class M3U8():
    """
    Makes an .m3u8 playlist
    """
    
    def __init__(self):
        """
        """
        
        self.song_map = {}
    
    def add_song(self, song_name:str, song_path:str):
        """
        adds a song to the .m3u8 files
        """
        self.song_map[song_name] = song_path
    
    def build_m3u8(self) -> str:
        """
        creates and saves the m3u8 file to disk
        """
        m3u8_data = '#EXTM3U\n\n'

        for song in self.song_map.keys():
            playlist_entry = f'#EXTINF: -1, {song}\n{self.song_map[song]}\n\n'
            m3u8_data += playlist_entry
        
        return m3u8_data
    
    def clear_playlist(self):
        """
        clears songs currently on playlist
        """
        self.song_map = {}