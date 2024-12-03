#!/usr/bin/env python

# ----------------------------------------------------------
# pysync Copyright 2006-2024 Ron Dippold
#
# See readme.txt and example.pysync for docs
# 
# Forgive me:  
#   This is a combination of twenty year old code with more 
#   recent code. There are obvious seams, like where
#   robocopy support was hacked in 8 years ago.
# ----------------------------------------------------------

VERSION = "v1.00"

import optparse, os, platform, shutil, subprocess, sys
import colorama
# import win32api is done below if running on windows

Fore, Style = colorama.Fore, colorama.Style

# ----------------------------------------------------------
# You can override any of these in your 
#   <COMPUTERNAME>.pysync file
# ----------------------------------------------------------

# define these as global so your *.pysync file can override them
global WINDOWS, ROBOCOPY, ROBOCOPY_CMD, RSYNC_CMD, PYSYNC_FILE_DIRS
global RSYNC_OPTS, ROBOCOPY_OPTS, EXCLUDE_FILES, EXCLUDE_DIRS

# Windows/Linux and what command to use by default
WINDOWS = ( os.name == 'nt' )
if WINDOWS:
    ROBOCOPY = True
    ROBOCOPY_CMD = shutil.which( 'robocopy' )
    import win32api
else:
    ROBOCOPY = False
    RSYNC_CMD    = shutil.which( 'rsync' )

# places to look for <COMPUTERNAME>.pysync
PYSYNC_FILE_DIRS = [
    os.getcwd(),    # current working directory
    os.path.join( os.path.expanduser("~"), ".pysync" ), # ~/.pysync/
    os.path.dirname( sys.argv[0] ) # where this script is
]

# Options to use for every rsync run
RSYNC_OPTS = [
    '--recursive', '--update', '--links', '--times',
    '--omit-dir-times', 
    '--del', '--delete-excluded',
    '--info=BACKUP,DEL,COPY,REMOVE',
    # '--ignore-case',  # only valid for cwrsync
    '--modify-window=5',
    '--itemize-changes',  '--stats',
]
                
# Options to use for every robocopy run
ROBOCOPY_OPTS = [
    "/mir",     # mirror
    "/xj",      # exclude links
    "/fft",     # assume FAT file times (2 second granularity)
    "/dst",     # compensate for daylight savings differences
    "/ndl",     # don't mention directories added/removed
    "/r:5",     # retry attempts
    "/w:5",     # seconds between retries
]

# Don't sync these files - wildcard, not regexp
EXCLUDE_FILES = [
    r"*Cache*",
    r"thumbs.db",
    r"*.tmp", r"*.log", r"*~", r"*.lock", r"*.bak",
    r"IconCache.db",
    r"pagefile.sys", r"hiberfil.sys", r"swapfile.sys",
    r"*NTUSER*",
    r"api-ms-win-*", r"ext-ms-win-*",
    r"*USRCLASS.DAT*", r"*UsrClass.dat*",
 ]
 
# Don't sync these dirs - wildcard, not regexp
EXCLUDE_DIRS = [
    r"$Recycle.Bin",
    r"*cache*",
    r"$GetCurrent",
    r"__gsdata__",
    r"System Volume Information",
    r"Diskeeper",
    r"RECYCLER",
    r"Flash Player",
    r".vs",
    r"Cookies",
    r"NetHood",
    r"PrintHood",
    r"Recent",
    r"Local Settings",
    r"ReportArchive",
    r"History",
    r"Temporary Internet Files",
    r"Temp",
    r"Recent",
  ]

# ----------------------------------------------------------
# Shouldn't have to touch anything below here
# ----------------------------------------------------------

# Error levels and colors to go with it
# TODO: enum.Enum
GOOD    = 0
OK      = 1
WARN    = 2
ERROR   = 3
SEVERE  = 4   
Color = { 
    GOOD  : Fore.GREEN + Style.BRIGHT,
    OK    : Fore.CYAN + Style.BRIGHT,
    WARN  : Fore.YELLOW + Style.BRIGHT,
    ERROR : Fore.RED,
    SEVERE: Fore.RED + Style.BRIGHT
}
# when printing job results
Pfx = {
    GOOD  : "-  ",
    OK    : "-  ",
    WARN  : "!  ",
    ERROR : "*  ",
    SEVERE: "** ",
}
  


# returns ( severity, errstring )
def do_job( job: dict, OPTIONS ) -> ( int, str ):

    job_name = job['name']   # make error strings more readable
    
    if 'windows only' in job and job['windows only'] and not WINDOWS:
        print( Color[WARN] + f"- skipping job '{job_name}', windows only" )
        print()
        return ( WARN, f"job '{job_name}' windows only" )
    if 'linux only' in job and job['linux only'] and WINDOWS:
        print( Color[WARN] + f"- skipping job '{job_name}', linux only" )
        print()
        return ( WARN, f"job '{job_name}' linux only" )

    robocopy_ignore = "robocopy ignore active" in job and job['robocopy ignore active']

    
    print( Color[GOOD] + "\n-----------------------")
    print( Color[GOOD] + job_name )
    print( Color[GOOD] + "-----------------------\n")
    
    SEPARATOR = os.sep
    if ROBOCOPY: 
        # needs to be a list because tuples can't be extended
        cmd = [ ROBOCOPY_CMD, ] + list( ROBOCOPY_OPTS ) + \
                list( job.get( "robocopy", [] ) )
        if robocopy_ignore:
            # no retry on failed copies, because there are
            # system files which will lock us up for weeks
            cmd += [ "/r:0" ]
        dirs =  list( job.get( "exclude dirs", [] ) ) + list( EXCLUDE_DIRS )
        if dirs:
            cmd.append( "/xd" )
            cmd.extend( dirs )  # don't quote!
        files = list( job.get( "exclude files", [] ) ) + list( EXCLUDE_FILES )
        if files:
            cmd.append( "/xf" )
            cmd.extend( files ) # don't quote!
    else:
        cmd = [ RSYNC_CMD, ] + list( RSYNC_OPTS ) + \
                list( job.get( "rsync", () ) )
        for glob in tuple(job.get('exclude dirs',() )) + tuple(EXCLUDE_DIRS):
            cmd.append( "--exclude" )
            cmd.append( glob ) # don't quote them!
        for glob in tuple(job.get('exclude files',() )) + tuple(EXCLUDE_FILES):
            cmd.append( "--exclude" )
            cmd.append( glob )
        
    err_str      = "OK!"  # nothing wrong yet
    err_severity = GOOD
    for dst0 in job['dst']:
        for src0 in job['src']:
            
            # Wherever the .pysync file was written, use the 
            # current os separator
            if SEPARATOR != '/':
                dst0 = dst0.replace( '/', SEPARATOR )
                src0 = src0.replace( '/', SEPARATOR )
            if SEPARATOR != '\\':
                dst0 = dst0.replace( '\\', SEPARATOR )
                src0 = src0.replace( '\\', SEPARATOR )
            src  = src0
                
            # TODO - this is OOOOLD code, now I'd use
            # os.path.join and os.path.split
            
            lefttrim = job.get( 'lefttrim', 0 )
            if lefttrim:
                dst2 = [ d for d in src0.split( SEPARATOR ) if d ]
                dst2 = dst2[lefttrim:]
                dst2 = SEPARATOR.join( dst2 )
            else:
                dst2 = src0
            # no ':' in the dirs added to the end of dst0
            dst2 = dst2.replace( ':', '' )
            dst  = dst0.rstrip( SEPARATOR ) + SEPARATOR + dst2
            
            if not OPTIONS.dummy and not os.path.isdir( dst ):
                try:
                    print( "Creating", dst )
                    os.makedirs( dst )
                except WindowsError as e:
                    print( Color[ERROR] + f"** {e} (skipping)")
                    if ERROR > err_severity:
                        err_severity = ERROR
                        err_str      = f"couldn't create dir '{dst}'"
                    continue
                    
            if not os.path.isdir( src ):
                print( Color[ERROR] + f"job '{job_name}' - no source dir '{src}'" )
                if ERROR > err_severity:
                    err_severity = ERROR
                    err_str      = f"no source dir '{src}'"
                continue

            # take any trailing / or \ off the back for ROBOCOPY
            # or so we can add regardless for rsync
            src = src.rstrip( SEPARATOR )
            dst = dst.rstrip( SEPARATOR )
            if not ROBOCOPY:
                # but rsync wants these!
                src = src + SEPARATOR
                dst = dst + SEPARATOR

            print( Color[OK] + f"[{job_name}] '{src}' -> '{dst}'" )

            # note we do NOT quote these, because we're not joining
            # them into a string, just passing the list
            if ROBOCOPY:
                cmdx = [ cmd[0] ] + [ src, dst ] + cmd[1:]
            else:
                cmdx = cmd + [ src, dst ]
            if OPTIONS.verbose:
                print( Color[OK] + str(cmdx) )
            if OPTIONS.dummy:
                continue

            sub = subprocess.Popen( cmdx, stdout=sys.stdout, 
                                    stderr=sys.stdout )
            sub.wait()
            #out, errs = sub.communicate()
            print( f"--  exit code {sub.returncode}" )
            print()
            if ROBOCOPY:
                # ROBOCOPY exit: https://ss64.com/nt/robocopy-exit.html
                if sub.returncode & 16 and SEVERE > err_severity:
                    err_severity = SEVERE
                    err_str      = f"serious error, no files copied"
                if sub.returncode & 4 and ERROR > err_severity:
                    err_severity = ERROR
                    err_str      = f"some mismatched files/dirs"
                if sub.returncode & 8 and WARN > err_severity:
                    if not robocopy_ignore:
                        err_severity = WARN
                        err_str      = f"some files failed to copy (could be system)"
            else:
                # man rsync
                if sub.returncode > 0 and ERROR > err_severity:
                    err_severity = ERROR
                    err_str      = f"rsync exit code {sub.returncode}"
            
    return ( err_severity, err_str )
            
def find_config_file( name: str ) -> str:
    # look to see if the file just exists where we told it
    if os.path.exists( name ):
        return name
    # then check the various directories
    for dir in PYSYNC_FILE_DIRS:
        fname = os.path.join( dir, name )
        if os.path.exists( fname ):
            return fname
    return None
    
   
if __name__=="__main__":

    colorama.init( autoreset = True )
    if WINDOWS:
        # don't pop up box when drive not found, just skip it
        win32api.SetErrorMode( 1 )  

    print( Color[GOOD] + f"-- pysync {VERSION} --" )
    print()

    # create parser, parse options
    parser = optparse.OptionParser()
    defconfig = platform.node() + ".pysync"
    parser.add_option( "-f", "--file", dest="config_file", action="store",
                        default = defconfig,
                        help=f".pysync file to use (default {defconfig})" )
    parser.add_option( "-N", "--dummy", dest="dummy", action="store_true",
                        default=False, help="Just show directories" )
    parser.add_option( "-v", "--verbose", dest="verbose", 
                        action="store_true", default=False )
    parser.add_option( "-l", "--list", dest="list", action="store_true",
                        default=False, 
                        help="Show available backup jobs (and exit)" )
    parser.add_option( "-w", "--wait", dest="wait",  action="store_true",
                        default=False, help="Wait when done" )
    OPTIONS, args = parser.parse_args()

    # find the config file, then try to run it
    fname = find_config_file( OPTIONS.config_file )
    if not fname:
        print( Color[SEVERE] +
            f"'{OPTIONS.config_file}' not found in: {", ".join(PYSYNC_FILE_DIRS)}" )
        sys.exit( SEVERE )
    try:
        with open( fname, mode = 'r' ) as f:
            # normally this would be a huge security hole, but you're
            # writing these for your own system
            exec( f.read() )
            print( Color[OK] + f"Using config file: {fname}" )
    except Exception as ex:
        print( Color[SEVERE] + f"Error while running '{fname}': {ex}" )
        sys.exit( SEVERE )
    
    # verify our robocopy or rsync exists
    if ROBOCOPY:
        if not os.path.exists( ROBOCOPY_CMD ):
            print( Color[SEVERE] + 
                    f"ROBOCOPY_CMD = '{ROBOCOPY_CMD}', not found?" )
            sys.exit( SEVERE )
    else:
        if not os.path.exists( RSYNC_CMD ):
            print( Color[SEVERE] + f"RSYNC_CMD = '{RSYNC_CMD}', not found?" )
            sys.exit( SEVERE )
                
 
    # allow for src and dst being just a string instead of a list
    for job in JOBS:
        if isinstance( job['src'], str ):
            job['src'] = [ job['src'] ]
        if isinstance( job['dst'], str ):
            job['dst'] = [ job['dst'] ]

    # if asked to list, just list and exit.
    if OPTIONS.list:
        for job in JOBS:
            explicit_txt = ""
            windows_txt  = ""
            linux_txt    = ""
            if 'explicit' in job and job['explicit']:
                explicit_txt = " [explicitly invoked only!]"
            if 'windows only' in job and job['windows only']:
                windows_txt = " [windows only!]"
            if 'linux only' in job and job['linux only']:
                linux_txt = " [linux only!]"
            print( Color[GOOD] + f"'{job['name']}': ",
                   explicit_txt, windows_txt, linux_txt )
            print( "    From:", ", ".join( job['src'] ) )
            print( "    To:  ", ", ".join( job['dst'] ) )
        sys.exit(1)

    # now see if each job should be run or not
    explicit = len(args)
    results = []
    for job in JOBS:
        if explicit:
            if job['name'] not in args: 
                continue
            args.remove( job['name'] )
        else:
            if job.get('explicit'):
                continue
        try:
            ( severity, err ) = do_job( job, OPTIONS )
            results += [ [ job['name'], severity, err ] ]
        except KeyboardInterrupt as e:
            print( Color[SEVERE] + f"{Pfx[SEVERE]}Interrupted in {job['name']}" )
            sys.exit( SEVERE )
            
    # asked for jobs, but never found them
    if explicit:
        for arg in args:
            results += [ [ arg, ERROR, 'job not found' ] ]
            
    max_severity = GOOD
    if results:
        print()
        print( Color[OK] + "Results:" )
        maxlen = 0
        for ( job, severity, err ) in results:
            maxlen = max( len(job), maxlen )
        for ( job, severity, err ) in results:
            print( f"  {Pfx[severity]} {job:<{maxlen}} - {Color[severity]}{err}" )
            if severity > max_severity:
                max_severity = severity

    if OPTIONS.wait:
        print()
        print( Colors[max_severity] + Pfx[max_severity] + "DONE")
        input()


