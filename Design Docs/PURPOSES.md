# What is this document?

v3.0.0 of spotDL was found to be lacking in many ways. While it fixed many of the issues
its predecessor had, it brought with it, many issues of its own. Primarily, poor
access-control and unnecessary functionality.

To address the issues of mucked-up class's, functions, modules and unnecessary
functionality this project here on works on zero-base-accounting - if you can't justify
it's need, you don't build it. The purpose of various functions, modules and classes
will be listed here and adhered to strictly. This document then, represents the primary
source of truth as to the requirement and responsibility of each unit of code.

# Structure

*This documents structure is yet to be decided*

## songObj (CLASS)

[PUR.] A lot of what spotDL does requires passing around of various details about songs.
The songObj serves as a ***single-point-of-access*** to all the various details we
might seek. The eliminates the need to query the same info multiple times from a server
while eliminating any ambiguity as to code unit return types. It also allows a consistent
interface to song details thereby adding to simplicity.

[RES.] songObj is meant to serve dual purposes - to act as an ***exchange currency***
through out spotDL and as a central repository of all known details of a given song.

## getSpotifyClient (FUNCTION)

[PUR.] Having different parts of code having to initialize spotifyClients when required,
would make for a lot of duplicate code. Serves as a ***single-point-of-access*** to 
a ***singleton spotifyClient***.

[RES.] ensure that only a single instance of spotifyClient exists throughout the codebase.