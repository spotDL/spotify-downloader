# What is this file?

A place where I put down my ideas regarding possible ideas, problems and
solutions to restructuring spot-dl.

# 09/08/2020 - 02:51 PM

Well, today is the third day of working of spot-dl and also the first day
of committing any code (mostly markdown), some of the stuff in workingDocs
might seem out of place and even whimsical but then who cares? The hope is that
it will provide you an insight into the ideas and thought processes behind the
new form of spot-dl.

The event that kickstarted this whole project is that another contributor who
worked on adding YTmusic as an additional source being 'unwilling to write all
of the code required to create a new provider' but had written the code to
search and filter YTmusic results. This is the first issue I'm going to
address.

# Search Providers

There are as of now (inkeeping with our core values) a need for two types of
search providers - song/album/playlist search providers and metadata search
providers. The idea is to design a standardized interface for both which can
be found [here](interfaces.md). The original version doesn't have a standard
interface for this and hence, any changes to search providers call for writing
of new classes and also inserting/deleting code all over the place to use the
new search provider.

The various user facing search and download options will be implemented by a
different class that utilizes the search results provided to do its thing.
Maybe I should name that class `soulOfSpotDl`, bad joke, I know. I might name
it the same anyways. All search providers have to be registered with the
`soulOfSpotDl` maybe like `soulOfSpotDl.registerProvider('music', searchClass)`
which then will be **accessed and used via its pre-defined interfaces only**.
It might be a good idea to provide some generic 'tools' to work with spotify
because expecting a contributor to learn how to use spotipy.

# 11/08/2020 - 12:19 AM

Very odd time to be programing indeed but then who cares? I was just looking
through some of the original spot-dl code by @ritek, he actually created
abstract classes to enforce interfaces. Its a good idea. Plan to do the same.

Interface enforcing abstract classes are a partial letdown, since you cant
define the output, pass on docStrings or enforce input args but they do the
work to an extent. Can consider writing up a custom metaClass. The current
metaClasses written up are at [Temp/interfaces.py](../Temp/interfaces.py).

Other things to carry on from the original spot-dl:
- Spotify client id + secret authorization: Look at
[authorize](../Ref%20-%20Original%20Code/spotdl/authorize) for reference and
inspiration.

- A wrapper around ffmpeg for transcoding songs: Look at
[encode](../Ref%20-%20Original%20Code/spotdl/encode) for reference and
inspiration.

- Remember those generic 'tools' to work with spotify? Look at
[helpers](../Ref%20-%20Original%20Code/spotdl/helpers)