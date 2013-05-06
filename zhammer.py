#!/usr/bin/python
# encoding: utf-8
'''
zhammer -- zram utility

zhammer is an advanced zram management utility

It defines classes_and_methods

@author:     Christ Schlacta
        
@copyright:  2013 Christ Schlacta. All rights reserved.
        
@license:    license

@contact:    aarcane@aarcane.org
@deffield    updated: Updated
'''

import sys
import os
import subprocess

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = 0.1
__date__ = '2013-05-04'
__updated__ = '2013-05-04'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

VERBOSE = 0

class ztab_entry_exception(Exception):
    '''exception class to handle ztab entry problems'''
    def __init__(self, msg):
        super(ztab_entry_exception, self).__init__(msg=msg)
        #self.msg = "Z: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg
    ___reason = None


class ztab_entry(object):
    number = None
    name = None
    entry_type = None
    size = None
    line = None
    options = {}
    known_options = set(['noauto']) #set of options we know how to handle
    my_known_options = set() # This should be overridden in base classes
    valid_options = {} #Processed list of valid options
    
    @staticmethod
    def parse(line = None, default = None):
        if line is None or line.strip() == "":
            raise (ztab_entry_exception("Attempt to parse uninitialized ztab_entry"))
        #print(line)
        #print(default)
        split = line.strip().split(None, 4)
        try:
            number = None
            name = None
            options = {}
            if type(default) is DEFAULTS:
                #print("Applying default settings")
                entry_type = default.entry_type
                size = default.size
                options.update(default.options)
            else:
                entry_type = None
                size = None
    
            tmp_val = ztab_entry.value_or_none(split[0])
            if tmp_val is not None: 
                number =  tmp_val

            tmp_val = ztab_entry.value_or_none(split[1])
            if tmp_val is not None:
                name = tmp_val
            
            tmp_val = ztab_entry.value_or_none(split[2])
            if tmp_val != None:
                entry_type = tmp_val
            
            tmp_val = ztab_entry.value_or_none(split[3])
            if tmp_val is not None:
                size = tmp_val
            
            if len(split) > 4:
                options.update(ztab_entry.parse_options(ztab_entry.value_or_none(split[4])))

            if name == "DEFAULTS":
                e = DEFAULTS(number,name,entry_type,size,options)
            else:
                if  entry_type is not None:
                    e = ztab_entry_type[entry_type](number, name, entry_type, size, options)
                else:
                    e = ztab_entry_type[default.entry_type](number,name,default.entry_type,size, options)
            return e
        except ztab_entry_exception, e:
            raise e
        except Exception, e:
            if DEBUG:
                import traceback
                traceback.print_exc(e)
            raise (ztab_entry_exception("Invalid ztab entry line: \n %s\n" % line ))
        except:
            raise (ztab_entry_exception("Invalid ztab entry line: \n %s\n" % line ))
    
    @staticmethod
    def value_or_none(value):
        """Some fields accept -.  We want to return none on those items"""
        if value == '-':
            return None
        return value
    
    @staticmethod
    def parse_options(options=None):
        ret = {}
        if type(options) is str:
            split = options.split(',')
            for option in split:
                option = option.split("=", 1)
                if len(option) == 2:
                    ret[option[0]] = option[1]
                else:
                    ret[option[0]] = True;
        return ret

    def __init__(self, number, name, entry_type, size, options):
        self.number = number
        self.name = name
        self.entry_type = entry_type
        self.size = size
        self.options = options
        #print "ztab_entry:init"
        #print self.entry_type
        self.known_options = self.known_options.union(self.my_known_options)
        self._process_known_options()

    def _process_known_options(self):
        self.valid_options = {k: v for k, v in self.options.iteritems() if k in self.known_options}

    def __str__(self):
        return "number: %s; name: %s; entry_type: %s; size: %s; options: %s;" %(self.number, self.name, self.entry_type, self.size, self.valid_options) 

    def __unicode__(self):
        return self.__str__()

    def online(self, process_all=False, process_type=None): #Do not override this
        #Can I online?
        can_online = False
        if self.name == 'DEFAULTS':
            can_online = True
        elif process_all:
            if self.valid_options.has_key("noauto"):
                pass
            elif process_type is None:
                can_online = True
            else:
                can_online = process_type == self.entry_type
        else:
            can_online = True

        if can_online:
            if VERBOSE:
                print "Onlining: %s" %(self)
            self.set_size()
            self._online()
        else:
            if VERBOSE:
                print("Unable to online %s") %(self)
    def set_size(self):
        try:
            size = self._expand_size();
            disksize = open("/sys/block/zram%s/disksize" %self.number, "w")
            disksize.write("%d\n" %size)
            disksize.close()
        except Exception, e:
            if VERBOSE > 0:
                print(e)
            return
    def _expand_size(self):
        size = str(self.size)
        if size.isdigit():
            return int(size)
        mult = 1
        modif = ""
        if modif == "":
            for mod in ["KiB", "KB", "K", "k"]:
                if mod in size:
                    modif=mod
                    mult = 1024
                    break
        if modif == "":
            for mod in ["MiB", "MB", "M", "m"]:
                if mod in size:
                    modif = mod
                    mult = 1024*1024
                    break
        if modif == "":
            for mod in ["GiB", "GB", "G", "g"]:
                if mod in size:
                    modif=mod
                    mult = 1024*1024*1024
                    break
        print("size1: %s" %size)
        size = size.replace(modif,"")
        print("size2: %s" %size)
        if not size.isdigit():
            raise ztab_entry_exception("Invalid Size Specification: %s" % self.size)
        size = int(size) * mult
        print("size3: %d" %size)
        return size

    def offline(self, process_all=False, process_type=None):
        #print ("Offline not implemented yet")
        can_offline = False
        
        if process_all:
            if self.valid_options.has_key("noauto"):
                pass
            elif process_type is None:
                can_offline = True
            else:
                can_offline = process_type == self.entry_type
        else:
            can_offline = True

        if can_offline:
            if VERBOSE:
                print "Offlining: %s" %(self)
            self._offline();
            self.reset()
        else:
            if VERBOSE:
                print("Unable to ofline %s") %(self)
    def reset(self):
        try:
            reset = open("/sys/block/zram%d/reset" %(int(self.number)), "w")
            reset.write("1")
            reset.close()
        except:
            pass

    def _online(self): # Override this
        pass
    def _offline(self):
        pass

    def run_command(self, cmd):
        if VERBOSE > 0: print(cmd)
        try:
            out = subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError, e:
            if VERBOSE > 0:
                print e
            out = e.output
        
        if VERBOSE > 0: print(out);
        return out
    
class DEFAULTS(ztab_entry):
    my_known_options = set(['devices'])
    def __init__(self,number,name,entry_type,size,options):
        super(DEFAULTS, self).__init__(number,name,entry_type,size,options)
        self.number = self.name = "DEFAULTS"

    def is_module_loaded(self):
        out = self.run_command("lsmod")
        if out.find("zram") == -1:
            return True
        return False
        
    def load_module(self):
        self.run_command("modprobe zram %s" % self.num_devices())

    def num_devices(self):
        devices = 0
        try:
            devices = int(self.valid_options['devices'])
        except:
            return ""
        if devices < 1:
            return ""
        out = self.run_command("modinfo zram")

        if out.find("zram_num_devices") == -1:
            return( "num_devices=%s" %devices)
        else:
            return( "zram_num_devices=%s" %devices)

    def _online(self):
        if self.is_module_loaded():
            self.load_module()
        
    def _offline(self):
        self.run_command("rmmod zram")

class swap(ztab_entry):
    my_known_options = set(['pri','swappiness'])
    def _online(self):
        try:
            self.run_command("mkswap /dev/zram%d" %int(self.number))
            pri=""
            try:
                pri = "-p %d" %int(self.options['pri'])
            except:
                pass
            self.run_command("swapon /dev/zram%d %s" %(int(self.number), pri))
        except:
            pass
        self.set_swappiness()

    def _offline(self):
        try:
            self.run_command("swapoff /dev/zram%d" %int(self.number))
        except:
            pass
    
    def set_swappiness(self):
        try:
            swappiness = int(self.valid_options['swappiness'])
        except:
            return
        self.run_command("sysctl -w vm.swappiness=%d" %swappiness)


class zfs(ztab_entry):
    my_known_options = set(['zpool'])

class zfscache(zfs):
    def _online(self):
        if self._get_pool() is None:
            return
        if self._is_healthy():
            self.run_command("zpool add %s cache /dev/zram%d" %(self._get_pool(), self.number) )
        pass
    def _offline(self):
        pass
    def _is_healthy(self):
        health = self.run_command("zpool status -x %s" %self._get_pool())
        if ("pool '%d' is healthy" %self._get_pool()) in health:
            return True
        return False
    def _get_pool(self):
        try:
            return self.valid_options['zpool']
        except:
            return None

class zfslog(zfs):
    def _online(self):
        print("Cowardly refusing to online zfs log.")
    def _offline(self):
        print("Cowardly refusing to offline zfs log.")

class fs(ztab_entry):
    def _online(self):
        print("fs module not yet implemented")
    def _offline(self):
        print("fs module not yet implemented")

ztab_entry_type = {'swap': swap,
                   'zfscache': zfscache,
                   'zfslog': zfslog,
                   'fs': fs}


class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''
    
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by user_name on %s.
  Copyright 2013 organization_name. All rights reserved.
  
  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0
  
  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-a", "--all", dest="all", action="store_true", help="Configure all zram devices with defaults")
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="Set verbosity level [default: %(default)s]")
        parser.add_argument("-t", "--type", dest="type", help="Only configure devices that match this type.  Useful only with -a")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument('-f', '--alternate-ztab-file', dest='ztab', type=file, default='/etc/ztab')
        parser.add_argument('action', help="online|offline", choices=["online","offline"])
        parser.add_argument('device', help="ztab number or named device to configure", nargs="?")
        
        # Process arguments
        args = parser.parse_args()
        
        action = args.action
        device = args.device
        global VERBOSE
        VERBOSE = verbose = args.verbose
        process_all = args.all
        process_type = args.type
        ztab = args.ztab
        entries = {'DEFAULTS': None,}
        if verbose > 0:
            print("Verbose mode on")
            print("Processing from ztab: %s" %(ztab))
            if process_all:
                print ("Processing all devices")
                if process_type:
                    print ("... of type %s" %(process_type))
            else:
                print(device)
        for line in ztab:
            line = line.split("#",1)[0].strip()
            if line == "" or line is None:
                pass
            else:
                e = ztab_entry.parse(line, entries['DEFAULTS']);
                if  e.number is not None:
                    entries[e.number] = e
                if e.name is not None:
                    entries[e.name] = e
                
        if verbose > 0:
            for key,value in entries.iteritems():
                print(key + ": " + str( value))
        
        to_process = ['DEFAULTS']
        
        if verbose > 0:
            print("Action: %s" %(action))
            print("Device: %s" %(device))
        
        if device is not None:
            if device == "DEFAULTS":
                pass
            elif entries.has_key(device):
                to_process.append(device)
            else:
                print("no such entry: %s" %(device))
                return 1
        elif process_all:
            keys = entries.keys()
            keys.sort()
            print(keys)
            for k in keys:
                try:
                    int(k)
                    to_process.append(k)
                except Exception, e:
                    pass
        else:
            print("Do what now?")
            return 2
        if verbose > 0:
            print("to_process: %s" %(to_process))
        
        if(action == "offline"):
            if process_all and process_type is not None:
                to_process.remove('DEFAULTS')
            if not process_all and device != "DEFAULTS":
                to_process.remove("DEFAULTS")
            if process_all:
                to_process.reverse()
        
        for k in to_process:
            v = entries.get(k)
            if verbose > 0: print "attempting to %s: %s" %(action, v)
            if action == "online":
                v.online(process_all, process_type)
            elif action == "offline":
                v.offline(process_all, process_type)
            if VERBOSE > 0:
                print("---")
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception, e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2
    
if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
        #sys.argv.append("-a")
        #sys.argv.append("-tswap")
        #sys.argv.append("zfscache0")
        #sys.argv.append('-h')
        #sys.argv.append('-fztab')
        #sys.argv.append("online")
        #sys.argv.append("zfscache0")
        #sys.argv.append("DEFAULTS")
        #sys.argv.append("Does_not_exist")
        
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'zhammer2_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())


