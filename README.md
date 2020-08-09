# Why this branch?

This branch was created for a very specific purpose - to restructure spot-dl so
that it is more scalable (can get bigger and more richly featured without major
effort/maintenance trouble). This fairly sizeable project is being undertaken
with one single underlying belief that the primary directive of any codebase
should be to manage complexity. The beauty of software systems/models is that
they can get infinitely big/complex, they aren't bound by the limitations of
the physical world. There is a dark side to this too, the human brain can't and
isn't designed to comprehend systems of any kind, small or big. We lack an
intuitive feel for it, we most certainly can't handle big interconnected chunks
of code - hence, the need to manage complexity.

Spot-dl grew from a fairly small project to it's current feature rich size. In
it's infancy, there was no need to 'manage complexity', it was small enough to
handle head on. As it grew, most contributors didn't put in a conscious effort
to manage the complexity, this isn't really any ones fault, those coders knew
how everything was connected. The average new guy/girl on the block isn't
willing to put in the effort required to understand the large interconnected
blocks of code that constitute spot-dl. This is an attempt to break it down,
manage the complexity. The reason this author repeats this point is because
to serve its purpose, there are some very specific needs to all code being
contributed here and hopefully hereon into the future.

# The requirements

- An conscious attempt to follow Object Oriented Programing. I realize that
most of you guys probably do so, for those of you who don't, please do. If you
don't know the principles of OOP or would like a refresher, look through 
[this](Temp/OOP.md).

- Compliance with the code guidelines setup [here](Temp/codeGuidelines.md).
and also the [core values](Temp/coreValues.md) of this project.