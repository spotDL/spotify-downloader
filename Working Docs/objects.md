# What is this file?

All classes that aren't implementing a predefined interface will be documented
here.

# Song

Describes details of Music search results.

| Attributes | | |
| --- | --- | --- |
| **Name** | **Type** | **Description** |
| songName | str | name of the song, doesn't include artist names |
| artists | list:str | a list containing the names of all artists involved |
| spotifyLength | int | length of song on spotify in seconds |
| youtubeLength | int | length of song on youtube in seconds |
| spotifyLink | str | the songs spotify URI |
| youtubeLink | str | the songs youtube URL |

<br><br>

| Functions | | |
| --- | --- | --- |
| *None* | | |

<br><br>

Notes,

- The youtubeLink attribute might have to change later if more download
sources are added. Suggested name of when that happens is `downloadLink`.
`downloadLink` is not being used now keeping in line with naming conventions
requiring descriptive variable names.

- Other details like album names have not been added here as the `Song` class
is meant only to describe the search results returned from the Music Search
Interface.

- In case the user would like to choose the song to be downloaded in the case
that spot-dl doesn't download the correct song the basic details that can be
provided to the user would include names of artists, song name, and song
length, hence the inclusion of a `spotifyLength` attribute.

 - The `youtubeLength` attribute has been included as the length of the song on
 spotify and youtube may not necessarily (and often do not) match.

 # Metadata

 Holds the metadata of a song.
 
| Attributes | | |
| --- | --- | --- |
| **Name** | **Type** | **Description** |
| songName | str | name of the song, doesn't include artist name |
| albumArtist | str | name of the main artist |
| contributingArtist | list:str | names of artists featured |
| album | str | name of the album |
| year | int | year of release |
| songNumber | int | int |
| genre | str | int |
| length | int | length of the song in seconds |

<br><br>

| Functions | | |
| --- | --- | --- |
| *None* | | |

Notes,

- I have considered using a dict instead of an object that just serves data
storage. I haven't ruled that out yet.

- Should every single parameter of the above be compulsory? I don't know yet.