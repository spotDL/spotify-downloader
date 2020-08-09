# What is this file?

# Objects

## Song

Describes details of Music search results.

| Attributes | | |
| --- | --- | --- |
| **Name** | **Type** | **Description** |
| songName | str | name of the song, doesn't include artist names |
| artists | list | a list containing the names of all artists involved |
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