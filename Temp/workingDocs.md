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