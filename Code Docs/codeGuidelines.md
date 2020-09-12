<!-- Coding guidelines to go here, all of them - from the simple to the obscure -->

# Code Guidelines

Various code guidelines we request you to follow through and through your code (at least the code
you contribute here). Some will seem important and useful, others dumb and inconsequential but
then... Whatever (no fancy reasons here).

<br><br>

# Index

1. Naming of
    - [Variables](#Variables)
    - [Functions](#Functions)
    - [Classes](#Classes)
    - [General Conventions](#General)

2. [Sizing of Modules/Classes/Functions](#Sizing)

3. [Documentation](#Documentation)

<br><br>

# Naming Conventions

Internal consistency in naming greatly reduces the effort in understanding the codebase by getting
rid of cognitive overhead allowing you to focus on what matters. This is especially useful in large
codebases. The following naming conventions are only for python.

## Variables

- Use Camel case naming - Uppercase the first letter of each word after the first. eg,
    - `songObject`
    - `randomVariableThatNoOneCaresAbout`

<br><br>

## Functions

- Use snake case - fully lowercase names with underscores instead of spaces. eg,
    - `download`
    - `save_to_disk`
    - `songObj.get_contributing_artists`

<br><Br>

## Classes

- Capitalize the first letter of each word. eg,
    - `DisplayManager`
    - `SongObj`
    - `Spotdl`

<br><br>

## General

- Use descriptive names - your names should convey the purpose. eg,
    - `car` or `bus` instead of `fourTire` when you are referencing a 4-wheeled vehicle
    - `download_song` instead of `get` you might also be *'getting'* song metadata - why the
        confuse the reader?
    - `DisplayManager` instead of `Manager` - *Was it 'DownloadManager' or just 'Manager'?
        Crappy naming...*

- Avoid abbreviations, if you can't use mnemonic abbreviations - stuff you can pronounce. eg,
    - `cLine` instead of `cne`
    - `DlManager` instead of `DlMngr`
    - `download_from_spot` instead of `download_fr_spfy`

<br><br>

# Sizing

500 line files are daunting - as someone new to the codebase, you don't know if you can get
through all of that code... Sizing limits prevent you from writing mammoth code, force you to
ruthlessly simplify and ensure proper abstraction (as it forces you to break-up any unusually
large classes/functions you might have)

- Python
    - Keep python lines ***under 90 columns in length***, i.e. 90 characters per line including indents
    - Keep python modules ***under 200 lines of code***, excluding comments, empty lines, docstring's.
    - Keep python classes ***under 100 lines of code***, excluding comments, empty lines, docstring's.
    - Keep python functions ***under 75 lines of code***, excluding comments, empty lines, docstring's.

- Markdown
    - Keep Markdown lines ***under 100 columns in length***, i.e. 100 characters including spaces
    - Keep Markdown files ***under 750 lines***, including comments and empty lines

Counting lines of python code is arduous, so you can use the `totalLNC.py`, `funcLNC.py` &
`classLNC.py` from the `.\dev utils\` folder to do the heavy lifting. Run them by passing
them a folder name. eg, `python '.\dev Utils\classLNC.py' .\spotdl`

<br><br>

# Documentation

With modern code editors like VS Code providing markdown-enabled docstring display when you hover
over a function or class, referencing documentation is easier than ever before - provided you can
write good in-line documentation.

- Docstring's for functions
    - Start with types of arg, arg name and purpose. Use markdown's code-syntax for arg type
        and arg name, followed by a colon and description
    - Note return type with `RETURNS` and an optional description of the same
    - Describe the purpose of the given function, and other quirks
    - Don't use coding terms except names of arg passed to function/class

- Control flow comments
    - Comment out control flow of your code before you start coding, use `#` for these comments
    - Indent control flow comments as required
    - Now, others who want to read your code don't have to put too much effort into figuring out
        the control flow
    - Don't use coding terms or reference functions and variables here except the most basic ones

- Notes about the code
    - Underline quirky behavior or details related to your code using comments, differentiate these
        from control flow comments by starting them with `#!` instead of `#`
    - Explain design decisions here
    - Feel free to reference what ever you want

- Your code itself
    - Good code is it's own documentation
    - Don't be afraid to visually block out your code using multiple constitutive blank lines

- An Example,
    ```python

    def download_img(imageUrl, savePath = '.\img.jpg'):
        '''
        `str` `imgUrl` : Url of the image to be saved

        `str` `savePath` : path at which file is to be saved

        RETURNS `bool`

        downloads image at `imageUrl` to `savePath`. Returns `True` if download is successful.
        Folders in `savePath` are not created, you'll get an error if they don't exist.
        '''

        # Setup a python do-while loop equivalent

        #! As users of this library usually have terrible internet connections, we
        #! attempt to download the image up to 10 times on a UrlError
        
        while True:
            try:
                # Attempt to read image as binary file
                #! This is the usual cause of errors
                
                imgData = urlopen(imageURL).read()




                # Save image to disk

                #! Though creating the required directories is an easy job, it is intensionally left
                #! out here as this lib has to run in highly restricted directory trees environments
                #! where the user doesn't necessarily have permissions to create directories.
                #! Assuming the user has no permission to create dirs, this code can still be used by
                #! him/her/them to save images without having to edit the code themselves.
                #!
                #! We return True on success, thereby exiting the function

                with open(savePath, 'wb') as file:
                    file.write(imgData)

                return True
    



            except UrlError or FileNotFoundError:
                if errorCount > 10:

                    #! Returns False on failing more than 10 times, exit func...
                    return False
                else:
                    errorCount += 1
    ```

    - There are only 11 lines of code, yet the function is 47 lines long. Is it worth it? Absolutely.
    The next guy who comes along won't wonder why you attempt to download an image 10 times and
    won't get rid of the loop thinking it to be pointless, he/she/they wouldn't attempt to create
    the necessary file directories as required  - something that seems like a more functional
    addition to the function than the while loop - knowing why that was left out in the first place.

    - The doc string allows someone who intends to use this function in their code a ready reference
    to what each arg is used for and more importantly, just what the return value does. On just
    another random day who would have ever thought that a 'download' function returning True means
    that to download was successful?

    - And the weird function structure makes sense without major head-whacking.