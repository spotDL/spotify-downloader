# What is this file?

This is where a list of the smaller code guidelines like variable naming will
be listed out. Some of the gains from the following guidelines might seem
negligible, but for large code bases (greater than 1000 lines), those marginal
gains will add up to sizable improvements.

# Guidelines

## General

- Keep line width under 80 characters. Both studies and experience state that
longer lines of code lead to higher incidence of errors and and increased
difficulty in understanding.

    ```python
    # Harder to handle
    logging.basicConfig(filename = 'blah.log', filemode = 'w', format = '%(levelname)-10s | %(name)-20s | %(message)-150s | %(funcName)-20s | %(pathname)s (ln:%(lineno)d)', level = logging.INFO)

    # Easier to handle, lines below 80 characters
    logging.basicConfig(
        filename = 'blah.log',
        filemode = 'w',
        format = '%(levelname)-10s | %(name)-20s | %(message)-150s | \
            %(funcName)-20s | %(pathname)s (ln:%(lineno)d)',
        level = logging.INFO
    )
    ```

- Comment out the control flow of your code before you start coding, it not
only makes your coding get done fast (from personal experience, I can back this
up) but also provides future contributors an on-spot guide/context to the code
they are reading.

- Use as few imports as possible (< 5). More imports are harder to track and
also increase to inter-dependencies b/w different pieces of code. What this
means is that a change is code in one of the many imports you use or one of its
dependencies will break your code and you'll be in for a long session of
debugging.

- Before you write production code (what actually goes into the project), write
up your concept in prototype code, your prototype code can be as messy as you
want. Experiment on your prototype code. This gives you a temporary familiarity
with the imports or ideas your trying to implement resulting is better
production code. Never repurposed prototype code for production.

- Write up documentation for your production code. Take it for granted that
software projects only grow in size and bigger codebases are harder to
understand. To keep a project maintainable, documentation is paramount.
Avoid writing too detailed documentation, the purpose of documentation is to
give a new contributor a base from which to start up while providing an
experienced contributor a quick reference. If your documentation is in html or
markdown, links are your best friend. Make the documentation. as easy as
possible to use.

- On openSource projects (like this one) commit often - as soon as your done
with one session. Commit your work even if it's incomplete.

<!-- Have to break 80 character rule here to render the print output correctly
as will be seen during runtime -->

- Avoid backslash notation, use a '+' instead
    ```python
    def randomFunction():
        print('This is a random function that prints a random message so that the \
            message length exceeds 80 characters and ends up using the backslash notation')

    # The above will print:
    # This is a random function that prints a random message so that the         message length exceeds 80 characters and ends up using the backslash notation
    ```
    ```python
    def randomFunction():
        print('This is a random function that prints a random message so that the ' +
            'message length exceeds 80 characters and ends up using the backslash notation')

    # The above will print:
    # This is a random function that prints a random message so that the message length exceeds 80 characters and ends up using the backslash notation
    ```

<br><br>

## Variables

- Use snake case naming. A constant naming style decreases the overhead
cognitive load of reading through the code. It might be an unconscious gain
but is well worth it in the case of large code bases.

- Use descriptive names. Variable names like `fourTire` is a bad variable name
because it doesn't tell you anything about how the variable functions. An
alternate better variable name would be `car` or `duneBuggy`.

- When using use mnemonic variables(pronounceable variable names). `gtwy` as an
acronym for `gateway` is a bad choice because, it can't be pronounced, `gway`
is comparatively better because it is pronounceable. Research shows that
mnemonic names are more easily remembered and discussed.

- Use positive names for boolean variables
    ```python
    # Not very easy to understand
    notAdult = True

    if not notAdult:
        # the person is an adult
        ...
    ```
    ```python
    # Easier to understand
    oldEnough = True

    if oldEnough:
        ...
    ```

<br><br>

## Functions

- Function naming to follow the same guidelines as for [Variables](#Variables).

- Avoid functions greater that 150 lines. Studies show that functions < 50
lines and functions > 150 lines show greatest level of errors.

<br><br>

## Classes

- Class naming to follow the same guidelines as for [Variables](#Variables).

- Avoid classes greater than 400 lines. Incidence of error increases
exponentially beyond 400 lines.

<br><br>

## Logging

- Use different logging levels (CRITICAL, ERROR, WARNING, INFO) as follows:
    - CRITICAL - Errors that can't or shouldn't be handled (like absence of
    write permission in the given location)
    - ERROR - Errors that can are being handled (think, list out of range
    error)
    - WARNING - Actions that should be done but can't (write song metadata
    can't be done because of media format)
    - INFO - Overview of what is being done (messages like 'retrieved
    songs from spotify playlist')

- The difference b/w ERROR and WARNING may not be very clear at first look.
WARNING is more like INFO. INFO is what is being done, WARNING is like negative
INFO logs (basically, what is not being done) while ERROR is what you'd find
in a try-except block - an actual error that you have expected and handled.

- Make minimal use of logging, logging is only to figure out what happened and
what went wrong not every last detail to the extent of the value of some random
variable.

- Keep log messages below 80 characters, if its longer chances are that it has
unnecessary details.

- Don't use programming references or reference variables in your logging
messages, the reader of the log may not necessarily know programing or know the
functioning of spot-dl thoroughly enough to understand what your referring to.

- Give a context for your logging messages. Use '>' to signal possible continuation

    ```python
    # Example log-file, only partial log presented here

    # Not very clear

    INFO        | All defined loggers have been configured
    INFO        | Creating authorized Spotify client
    INFO        | Client creation successful
    INFO        | Returning cached client
    INFO        | Obtained authorized Spotify client

    # Clearer

    INFO        | All defined loggers have been configured
    INFO        | Spotify client Primary initialization >   # context line
    INFO        | Creating authorized Spotify client >
    INFO        | Client creation successful
    INFO        | Requesting Spotify client >           # context line
    INFO        | Returning cached client               # should possess '>'
    INFO        | Obtained authorized Spotify client
    ```

- Once you have working code, read the error free logs and adjust your log
messages. For example, in the above log example, 'Returning cached client'
should, in theory be 'Returning cached client >' because the next log message
is clearly a continuation of the same *flow of events* but
`getAuthorizedSpotifyClient` doesn't know of the existence of the logger
message that follows it, the author didn't anticipate this. A simple solution
is to delete `logger.info('Obtained authorized Spotify client')` (see below
code). The only way that would strike you is if you read the working code's
log messages to figure out if it was readable. So, read the logs once in a
while.

    ```python
    # python code for the 'clearer' version of the log from the previous
    # point

    logger.info('Requesting Spotify client >')  # assumes that below function
                                                # writes log messages

    client = getAuthorizedSpotifyClient()       # 'Returning cached client' 
                                                # log message from here

    logger.info('Obtained authorized Spotify client')       # To be deleted

    ```

<br><br>

## Go [back](../README.md#The%20requirements) to where you left off