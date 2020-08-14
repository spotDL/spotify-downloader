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
because expecting a contributor to learn how to use spotipy is a tall order.

# 11/08/2020 - 12:19 AM

Very odd time to be programing indeed but then who cares? I was just looking
through some of the original spot-dl code by @ritek, he actually created
abstract classes to enforce interfaces. Its a good idea. Plan to do the same.

Interface enforcing abstract classes are a partial letdown, since you can't
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
[helpers](../Ref%20-%20Original%20Code/spotdl/helpers) for reference and
inspiration.

# 11/08/2020 - 01:49 AM

After going through my handy Python Essential Reference, Fourth edition, it has
dawned on me that you can drastically alter the behavior or a class but you
can't enforce return types and it seems to me that having an Abstract Base
Class (ABC) for the interfaces might actually be a drag. On one hand, they
superficially enforce interface implementation on the other hand, they add an
additional link b/w various modules, the need to know the names of the ABC's
(so they can be inherited from) and don't even enforce inputs or outputs. The
killing blow is probably that a coder who intends to write a new better search
provider or a replacement for the current providers can implement the required
interfaces directly including the necessary inputs and output types. The aim
of this exercise is to simplify spot-dl so ABC's for interfaces got to go. Sad.

# 11/08/2020 - 04:50 PM

As to the client_id and client_secret used throughout to authorize spotify,
they can be found in the
[config.py](../Ref%20-%20Original%20Code/spotdl/config.py) file. The original
spot-dl used generic loggers, I plan to use hierarchal loggers. So once I get
the loggers and help tools up. Work should ease up.

# hierarchalLogging

The basic hierarchal logging setup is up and running, the relevant files can be
found at [loggingConfig.py](../Temp/loggingConfig.py), It will probably see a
lot more loggers defined over the course of dev. Some updates have been made to
the code guidelines. Notes on the design of `loggingConfig.py` have been added
[here](../Working%20Docs/Design%20Notes.md).

# Authorization

The classes required for authorizing spotify is done, the file is almost 98%
original code, all I did was rename some variables, allow the use of request
sessions (for performance considerations) and deal with a rather annoying
(._sessions not defined) error and renamed a file. Might have to figure the
whole package structuring thing. My focus at the moment is on completing the
'tools' so I can get others into this.

# Ideas

So, today I'm going to work on those spotify 'tools'. Since downloading takes
up quite some time, I'm considering using multiprocessing for that.

# Well, another day, new problems

For starters, I tried skinning VLC. It looks a lot cooler now but functionally
it's weird. Now, about the code. I'm confused as to what to allow into metadata
because, on one hand more details, the better, and on the other hand, more
details, more complex - something I'm seriously trying to avoid. So lets see,
just why do we need metadata?

- To accurately identify songs. This could use,
    - song name
    - album name
    - artist name(s)    (apps read contributing artists as main artist)
    - song length

- Some sugar, stuff that complements other metadata points. This would include,
    - track number (within it's parent album)
    - genre
    - album release date/year
    - album artist

- Other notable stuff Spotify provides:
    - label             (publisher or encodedBy ?)
    - copyright
    - explicit or not

- What can be set using python libraries:
    - The above and a lott more details that no one would ever look up

What does all of this mean? the first 4 are mandatory, the next 4 are preferable,
the rest could possibly used at some point of time, but no guarantees. In the
name of simplicity and minimalism or as jobs famously said - keep the core, get
rid of the rest - don't make the cut. only the first 8 details to be kept and a
little extra...

In essence, all that's left is:
- Song related:
    - song name
    - contributing artists (inclusive of main artist)
    - track number
    - genre
    - length

- Album related:
    - album name
    - album release date/year
    - album artist

- Other Utilities:
    - album art URL

The one thing I have to do the next commit is update the interface/related
object docs and add genre lookup to SpotifyHelpers.