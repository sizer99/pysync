# pysync

Copyright 2006-2024 Ron Dippold
sizer99 [at] sizer99.com

## Table of Contents

- [Versions](#versions)
- [Overview](#overview)
- [Caveats](#caveats)
- [Install](#install)
- [Configuring Backup Jobs](#configuring-backup-jobs)
- [Usage](#usage)

## Versions

```
 V0.10 - 2011 Oct 15 - Split out .pysync files
 V0.21 - 2012 Oct 10 - Add lefttrim, explicit
 V0.30 - 2017 Dec 14 - Add Robocopy option
 V1.00 - 2024 Dec 02 - Release by request o-o, add docs,
                       add shutil.which to find robocopy/rsync,
                       add summary view at end
 V1.01 - 2024 Dec 02 - Small fixes on immediately discovered things
```

## Overview 

Easy rsync/robocopy for Windows or Linux (and probably Mac
with rsync). This is my personal thing I've been using for 
20 years so I can have easy backups on windows or linux,
may or may not be useful for you!

The Problem:
- Every night I want to back up certain important directories.
- Every week I want to plug in my giant backup SPAN and back
  up everything, but blindly copying everything I want backed
  up from every machine (over network too) would take > 24 hours.

The Solution:
- Only copy things that have changed (mirroring).
- rsync does this for Linux, robocopy does this for Windows.

Problem 2:
- The syntax is pretty annoying for both and the commands get very long.

Solution 2:
- This program will let you just say what things you want mirrored
  and it will worry about the syntax.
  
  
## Caveats 

> [!WARNING]
> Make sure you understand these limitations

- This does not do any versioning. If you changed foo.txt, the new
  foo.txt clobbers the old foo.txt in the backup. If you need
  versioning use something else.
  
- robocopy and rsync can only access what they have permissions to
  access, i.e., whatever the shell permissions are. If you really need
  to back up *everything* you will probably need to run this as 
  root (linux) or administrator (windows).


## Installation

You need python 3 installed. Then, 

On Windows: 
  `pip install pywin32 colorama`
  
On Linux:
  `pip install colorama`
  
colorama lets me color output, so green is good, red is bad.
pywin32 lets me set it so python doesn't pop up an error window 
   every time a directory you're trying to back up to isn't mounted.
  
  
## Configuring Backup Jobs

Create a file named COMPUTERNAME.pysync - if your computer name
is FOOBAR, then FOOBAR.pysync. On either windows or linux, 'hostname'
in the command window will tell you what it is. Case sensitive!

You can also just copy and rename example.pysync to FOOBAR.pysync 
then edit it for your use.

COMPUTERNAME.pysync can override some script variables (see below) 
and contains a list of jobs:
```python
    JOBS = [ 
         <job>, 
         <job>
    ]
``` 
These variables are all set by pysync.py but can be
overridden in your COMPUTERNAME.pysync:
```
    ROBOCOPY = True / False - use robocopy instead of rsync.
               The default is True on Windows, False on Linux.
    ROBOCOPY_CMD = "<where is robocopy.exe>"
    RSYNC_CMD = "<where is rsync>"
    PYSYNC_FILE_DIRS = [ <directories where pysync looks for your
                         COMPUTERNAME.pysync ]
    RSYNC_OPTS = [ <options to use for every rsync cmd> ]
    ROBOCOPY_OPTS = [ <options to use for every robocopy cmd> ]
    EXCLUDE_FILES = [ <wildcard patterns of files to ignore> ]
    EXCLUDE_DIRS = [ <wildcard patterns of directories to ignore> ]
``` 

PSYNC_FILE_DIRS, RSYNC_OPTS, ROBOCOPY_OPTS, EXCLUDE_FILES, and 
EXCLUDE_DIRS in pysync.py are just lists, so your COMPUTERNAME.pysync
can append to them or delete from them as needed.
 
 Each job looks like this.  Options are explained in more detail
 below, and please look at example.pysync to see it in action.
```python
    { 
        "name" : r"descriptive/command line name",
        "src"  : [ <comma separated source directories> ],
        "dst"  : [ <comma separated dest directories> ],
        "exclude files" : [ <comma separated file patterns 
                          to exclude> ],
        "exclude dirs" :  [ <comma separated dir patterns 
                          to exclude> ],
        "lefttrim" : <# of dirs to trim on left of path> (Def: 0),
        "explicit"  : True/False (Def: False),
        "robocopy": [ <any extra robocopy parms,
                        like /mt:4 for 4 threads at once> ],
        "robocopy ignore active" : True/False (Def: False),
        "rsync": [ <any extra rsync parms> ],
        "windows only": True/False (Def: False),
        "linux only", True/False (Def: False),
    },
```

Make sure you have a comma at the end of every "[key]" : [value]!
Technically you don't need it on the last one, but safest to just
do it on all of them so you don't forget any.
   
For windows directory names with \, there are three ways
to deal with them:
  - _Do NOT use `"c:\foo"`_, python will read this as `"c:foo"`
   and things will fail
  - use raw strings, like `r"c:\foo"`
  - change \ to /, like `"c:/foo"`
  - double the \\, like `"c:\\foo"`

```
"exclude files": 
    ex:   "exclude files": [ "*.obj", "*.tmp" ],
    pysync.py also has an RSYNC_EXCLUDE of patterns which 
    will be added to the "exclude files" of all jobs.
"exclude dirs":
    like "exclude files", but for dirs!

"explicit": 
    If True, the job is not run on generic use and must be
    explicitly invoked from the shell like 'pysync.py [name]'

    This lets you have jobs ("explicit":False) which are just 
    run normally all the time and special jobs ("explicit":True) 
    which are only run when you really want them.

"lefttrim":
    The created folder tree in "dst" will include the entire 
    src tree (c/foo/bar), unless you use lefttrim. If you 
    sync c:\blah\stuff to d:\backups, you will normally get
    d:\backups\c\blah\stuff. 

    "lefttrim" is how many directories on the left to trim 
    from src. To use the precious example, if you wanted
    d:\backups\stuff instead of d:\backups\c\blah\stuff,
    set "lefttrim" : 2.
    
"robocopy ignore active":
    If using Robocopy, and trying to back up active system files,
    system, like c:/Users, you will get constant fails on open
    files the system owns. You can never read these and robocopy
    will lock up on them for 30 seconds each time. Use this to
    ignore those - note this will also ignore other files that
    fail to copy for other reasons!
    
"windows only":
"linux only":
    These jobs are ignored if you're on the other OS.
```
        
See 'example.pysync' for exactly how I back up one of my
desktops at home!
    
    
## Usage

In the simplest case, you just run pysync.py, either with 'pysync.py'
or 'python pysync.py'. If your computer name is FOOBAR, it will look
for FOOBAR.pysync in 1) the current directory, 2) ~/.pysync/, 3) 
the directory where pysync.py is. Then it will just run all the
jobs you have listed. Done!

Options:
```
    --help
        see full help
    -f [other.pysync]
    --file [other.pysync]
        use other.pysync file instead of COMPUTERNAME.pysync
    -l
    --list
        don't do any syncing, just show all the jobs available
    -N
    --dummy
        don't actually do any syncs, just process configs, good for
        error checking
    -v
    --verbose
        show the actual command line used (as a list)
    -w
    --wait
        wait for you to hit enter when done
```
You can also list the explicit jobs to run. For example if you have an
explicit sync for h:\movies to d:\ named "Movies to D" then you could
run it with 
    `pysync.py "Movies to D"`
    
If you do this, it won't run any jobs except the one(s) you list.
