# What is this file?

Details as to why some classes/files/other code decisions were made the way
they were made are noted here in the hope they might clarify some doubts you
as a contributor may have as to the same.

# Design of Hierarchal Logging

The purpose of a log is not to provide the utmost information, it is to provide
the bare minimum required information to diagnose the problem. It is for those
reasons that  details like time (asctime) and module name (module) were removed.
The module name doesn't necessarily provide the level of nesting ('topModule >
Blah > module' might simply show up as just 'module' in the log) and can cause
confusion between similarly named but different files. The module name has been
replaced by the more accurate file path + line number. Time for our purpose is
irrelevant. The function (funcName) name has been retained as a quick reference
( its easier to recall than file path + line number). The logger name has been
retained as an extra measure for quick identification.