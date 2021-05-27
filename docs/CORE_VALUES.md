<!--- mdformat-toc start --slug=github --->

# CORE VALUES

## What is this file?

This is where we outline the fundamental ideas by which we decide what to do, what to keep
and what to remove from spotDL.

## The Deciding Factors - Our values

- Simplicity:
  - What can we remove? Is this necessary to most (~80%+) of users?
  - Can we make it easier to use? Fewer steps?
- Focused Functionality:
  - spotDL is to download "content" from Spotify. Does this help doing that? (very narrow
    focus here people) A.K.A - is this a "need to have"?
  - if its a "nice to have", will most of the users use it? (note: its "most users **use**",
    not "most users **want**")
- Users first, provided its maintainable:
  - Will this do good to the users? They might have not even thought about it, it might make
    things more complex (more understanding of spotdl required to use it) but will it benefit
    the majority (~80%+) of them in the process?
  - Provided it helps the users, if it has a big impact on maintainability, its still a no-no.

If a contribution satisfies at least 2 of our deciding values it gets accepted, else, it
doesn't.

## A few general notes

1. The term 'users' is thrown around a lot. For a project like `FFmpeg`, users is that group
   of coders who are unafraid of a command-prompt (it says so on the downloads page itself).
   Here, '***users***' refers not to developers but normal *homo sapiens* - just about
   anybody who wants to download "content" from Spotify.

2. The term 'maintainability' has also been given significant weight. This is used in 2
   senses of the word:

   - General Simplicity - Can I read the code \***once** and understand what is going on?
   - Industry standard maintainability measures (the same one outlined on betterCodeHub)

3. The ideas outlined here are still very much a work in progress and is open to discussion
   but, we will stick to these. Some of the biggest companies & many more ambitious projects
   has all fallen to ruin because of the 'undisciplined pursuit of more'. That should not
   happen here. This is not so much of an outline of what we should do but, an outline of
   what '**we should not do**'.

4. You're encouraged to question each contribution/existing functionality as required.
