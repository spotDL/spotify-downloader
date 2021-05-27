<!--- mdformat-toc start --slug=github --->

# CONTRIBUTING

## Which contributions get accepted and which ones don't?

For the sake of maintainability and ease-of-use standards, we are not able to accept all
contributions that come to spotDL - don't get us wrong,
**ALL CONTRIBUTIONS ARE WELCOME...** So just which contributions get accepted and which
ones don't? That's what we're here to answer.

______________________________________________________________________

## A short note to contributors

1. Further on in this document, we use the term 'Users' interchangeably for both people who
   use spotDL as a command line tool and those who use spotDL as a library.

2. These requirements are aimed at helping future contributors (people like you) more than
   its aimed at users, code quality and other such things.

3. Most of the requirements we need for a contribution to be accepted overlap with each
   other, so our 5-point requirements is more of a 3.5-point requirements.

4. Yes, there might be times when you can't both improve spotDL and stick to the
   requirements, in those rare cases, focus on improvement first and do your best ot meet the
   requirements. Sometimes, you have to take a step back to take several forward.

5. Most of the requirements are subjective to an extent. In your view, your code might meet
   the requirements, in reality, from the experience handling many, many previous
   contributions, this might not be the case.

6. The maintainers have no obligation to accept your contribution just because you put in a
   lot of effort into it, so please feel free to open an issue about what ever it is that you
   wish to contribute to get in touch with maintainers before you put in all that effort.
   The maintainer will do their best to help you with your contributions.

______________________________________________________________________

## The basic requirements of any contribution

1. **'Ease-of-use'** and **'minimal user-know-how'**

   - *If an application has a steep learning curve, I'd rather not use it* - Everybody

   - Your users might not always be fellow programmers, ensure that your contribution makes
     spotDL easier to use both as a tool and as a library or at least don't make it harder.
     Making it easier to user means shallow learning curves and fewer steps as a script and
     'self-contained code' as a library, that way users (coders) don't need to peek lower-level
     code to understand just what the hell your code does, neither do future contributors have
     to peek too - They are the guys who actually need to understand your code.

   - eg.

     - spotDL v2 used a unix style command-line interface, spotDL v3 uses a much simpler command
       line interface that doesn't require any of the unix style input flags like `-d` or
       `--download`, for a user, thats less stuff to type (easier to use) and also less stuff to
       know - if the user is not a programmer, he/she/them don't have to learn to type unix-style
       commands.

     - every function has a standardized docStrings and type definitions, library users (other
       coders) don't need to look at the source code to either figure out the type of inputs to
       be passed or what the function does. Thats less things they have to look, refer or figure
       out. As a programmer you've probably wished that people wrote code like that, you and I we
       might as well start.

2. **Minimum steps** b/w the user and the end result

   - *'Civilization progresses by increasing the number of important actions that one can
     perform without thinking'* - Alfred North Whitehead

   - You can put in as many intermediate steps as you require internally to get something done
     but, you either decrease the steps b/w the user and what the user wants or at least, don't
     increase the number of steps.

   - eg.

     - In early revisions of spotDL, search utilities written to get playlist tracks returned
       spotify links which the user (programmer during use as a library) had to then pass to a
       `SongObj` constructor and then further pass the song object to the downloader. Now, the
       search utilities to get playlist tracks directly returns a list of `SongObj` - thereby,
       eliminating 1 step b/w the user (programmer) and the end result even though there is the
       additional intermediate step of passing the spotify links to the `SongObj`.

     - In spotDL v2 command line, the user (the guy downloading songs) would first have to run
       `spotdl --list $playlistLink` to write all songUrl's to a text file and then pass the text
       file to the spotDL script in the next step which would then re-query spotify for song
       details and proceed to download the song. In spotDL v3, all you have to do is run
       `spotdl $thing` where 'thing' might be a song, album, playlist or a song search query and
       it goes about getting the requisite tracks and downloading them eliminating 2-3 steps b/w
       the user (guy downloading songs) and the end result (downloaded, tagged songs)

3. **Simplicity** and **readability** of code

   - *The primary job of a programmed is to manage complexity* - Code Complete, Steve McConnell

   - Look man, seriously, software can get insanely complicated. In the real world there are
     physical limits to complexity, there is no such limit in software - thing can get as
     complicated as you wish but, the human brain is not designed to understand 'systems'. We
     have no intuitive feel for 'software systems' like we do for running down the stairs (try
     running down the stairs while looking at your feet, you'll understand just how intuitively
     you move around), in other terms - you can slowly put together complex systems but,
     others can't understand them the way you do. Beyond a point even you can't predict how
     everything will work together. Every programmer at some point of time has fixed a bug only
     to realize that the fix created another bug - that your biological incapability to
     understand systems. So, make it a point to keep things simple when you code, and simplify
     your code later.

   - Your not going to stick around forever, eventually someone else has to take over. Make
     their job easier, write code that is 'easy to understand and contribute to'

   - eg.

     - spotDL v3 was written from scratch, why? To simplify it. The fact that it went from
       approx. 47 files in v2 to just around 12 files in v3 with almost no loss of functionality
       is a good measure of the effort that went into simplifying spotDL.

     - almost all naming, be it of functions, variables or classes in v3 is meant to describe the
       functionality of that variable/function/class to some extent. As tempting as it is to
       name variables like `x`, they got more descriptive names like `totalSongCount`. Most
       function run into a 100+ lines while the actual code is just 33 lines and with a little
       'smart coding' possibly reducible to 20 odd lines, why? The code is written to be 'read
       and understood' not to 'save disk space' - your writing for the next contributor, not just
       for some feature you want.

4. Documentation, Documentation, some
   **more documentation; Write documentation into your code.**

   - *good code is its own best documentation* - Code Complete, Steve McConnell

   - In an ideal world, people would write such clear, readable, understandable code that there
     would be no need for documentation. Have a doubt? Read the source code... We don't live
     in that world. You know the code you wrote better than anyone else, write documentation
     for it. It doesn't have to be much - what are the inputs, what is the type of each input,
     what does that bit of code do, any special quirky behavior to look out for - thats all you
     need to put down. This will help users (other programmers using spotDL as a library)

   - The hardest part of contributing is going through old code and figuring out what does
     what, help out future contributors with that - use comments, use them as much as possible.
     Put in reminders when your leveraging some weird python behavior, put in notes on just
     what a particularly important code-block is doing, notes about docString-less functions
     that have been imported and used and just about anything that could use additional notes
     about it.

   - eg.

     - every single function in spotDL v3 has a markdown formatted docString that describes the
       basics required for documentation.

     - every single place in spotDL v3 where python interpreting `None` as `False` has been used,
       has an accompanying comment - `#! python evaluvates 'None' as 'False'` - its simple,
       right? WRONG. Not a lot of python programmers even know about this 'behavior quirk' of
       python.

5. Justified existence

   - *I write/accept code for 80% of users, not the 20% with special needs* - A maintainer,
     Vue.js

   - The bigger a program gets, the harder it is to manage, improve, extend and maintain. From
     experience the **Pareto principle** applies to code too - 20% of the code accounts form
     80% of the functionality - So, in the name of maintainability, don't bother writing the
     remaining 80% of code that provides only 20% of the functionality. If you are hellbent of
     doing so, make a fork of spotDL, well even put up a link to your fork for other who
     desperately need that 20% functionality.

   - Subject your code to [Zero-base accounting](/docs/code/CODE_GUIDELINES.md), it helps get
     rid of all the 20% features you feel tempted to build - it'll also spare you that much
     time and effort.

   - eg.

     - spotDL v2 was far more feature rich than v3, what did 99% of users use spotDL for? To
       download songs. spotDL v3 got rid of all the additional, 'nice-to-have' features and
       focused solely on downloading songs. Some might even say that it's under-featured, we
       can't really argue with that, but we have no intentions of changing that.

______________________________________________________________________

## Setup Local Environment for Development

1. Clone this repository

   ```bash
   git clone https://github.com/spotDL/spotify-downloader.git
   cd spotify-downloader
   ```

2. Setup venv (Optional)

   - Windows

     ```bash
     py -3 -m venv env
     .\.venv\Scripts\activate
     ```

   - Linux/macOS

     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install requirements

   ```bash
   pip install -e .
   ```

4. Use as command (no need to re-install after file changes)

   ```bash
   spotdl [ARGUMENTS]
   ```
