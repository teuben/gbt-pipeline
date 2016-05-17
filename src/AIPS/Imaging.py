# Copyright (C) 2007 Associated Universities, Inc. Washington DC, USA.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning GBT software should be addressed as follows:
#       GBT Operations
#       National Radio Astronomy Observatory
#       P. O. Box 2
#       Green Bank, WV 24944-0002 USA

# $Id$

import fitsio

import sys
import os
import glob
import subprocess
from collections import namedtuple
import socket


class Imaging:

    def __init__(self,):
        if 'arcturus' != socket.gethostname():
            print
            print 'For imaging, please run this command on machine name: ',
            print 'arcturus.gb.nrao.edu'
            print 'If you are on arcturus, please report this error.'
            print
            print 'If you only want to calibrate your data, but not image'
            print '  use the parameter --imaging-off'
            sys.exit(-1)
        pass

    def run(self, log, terminal, cl_params, mapping_pipelines):

        log.doMessage('INFO', '\n{t.underline}Start imaging.{t.normal}'.format(t=terminal))

        # ------------------------------------------------- identify imaging scripts

        # set the tools directory path
        # and location of the needed scripts and tools
        # if these are not found, turn imaging off
        pipe_dir = os.path.dirname(os.path.abspath(__file__))
        tools_dir = '/../'.join((pipe_dir, "tools"))

        load_script = '/'.join((pipe_dir, 'convert_and_load.py'))
        map_script = '/'.join((pipe_dir, 'image.py'))

        aipspy = '/'.join((tools_dir, "aipspy"))

        log.doMessage('DBG', "Pipeline directory", pipe_dir)
        log.doMessage('DBG', "Load script", load_script)
        log.doMessage('DBG', "Image script", map_script)
        log.doMessage('DBG', "aipspy", aipspy)

        # if the user opted to do imaging, then check for the presence
        # of the necessary imaging scripts (load.py, image.py, aipspy).
        if not os.path.isfile(map_script) or not os.path.isfile(load_script) or not os.path.isfile(aipspy):
            log.doMessage('ERR', "Imaging script(s) not found.  Stopping after calibration.")
            sys.exit()

        MapStruct = namedtuple("MapStruct", "nchans, window, start, end")

        maps = {}
        for mp in mapping_pipelines:
            nchans = int(mp.mp_object.row_list.get(mp.start, mp.feed, mp.window, mp.pol)['NCHANS'])
            maps[MapStruct(nchans, mp.window, mp.start, mp.end)] = set()

        for mp in mapping_pipelines:
            nchans = int(mp.mp_object.row_list.get(mp.start, mp.feed, mp.window, mp.pol)['NCHANS'])
            maps[MapStruct(nchans, mp.window, mp.start, mp.end)].add(mp.feed)

        log.doMessage('DBG', 'maps', maps)

        for thismap in maps:

            aipsinputs = []

            log.doMessage('INFO', 'Imaging window {win} '
                          'for map scans {start}-{stop}'.format(win=thismap.window,
                                                                start=thismap.start,
                                                                stop=thismap.end))

            # skip pipeline runs from imaging that have >32k channels b/c they will fail
            #   with idlToSdfits, 2**15 ~ 32k
            if thismap.nchans > 2**15:
                log.doMessage('WARN', 'Found spectra with > 32k channels.  Skipping.')
                log.doMessage('WARN', 'This can not be imaged because of a limitation in '
                              'the idlToSdfits data format converter.  Please '
                              'see the Pipeline User\'s Guide for a workaround using '
                              'the \'sdextract\' tool.')
                continue

            scanrange = str(thismap.start) + '_' + str(thismap.end)

            imfiles = glob.glob('*' + scanrange + '*window' +
                                str(thismap.window) + '*pol*' + '.fits')

            if not imfiles:
                # no files found
                log.doMessage('ERR', 'No calibrated files found.')
                continue

            # filter file list to only include those with a feed calibrated for use in this map
            feeds = map(str, sorted(maps[thismap]))

            ff = fitsio.FITS(imfiles[0])
            nchans = int([xxx['tdim'] for xxx
                          in ff[1].get_info()['colinfo']
                          if xxx['name'] == 'DATA'][0][0])
            ff.close()
            if cl_params.channels:
                channels = str(cl_params.channels)
            elif nchans:
                chan_min = int(nchans*.02)  # start at 2% of nchan
                chan_max = int(nchans*.98)  # end at 98% of nchans
                channels = str(chan_min) + ':' + str(chan_max)

            aips_number = str(os.getuid())
            aipsinfiles = ' '.join(imfiles)

            if cl_params.display_idlToSdfits:
                display_idlToSdfits = '1'
            else:
                display_idlToSdfits = '0'

            if cl_params.idlToSdfits_rms_flag:
                idlToSdfits_rms_flag = str(cl_params.idlToSdfits_rms_flag)
            else:
                idlToSdfits_rms_flag = '0'

            if cl_params.idlToSdfits_baseline_subtract:
                idlToSdfits_baseline_subtract = str(cl_params.idlToSdfits_baseline_subtract)
            else:
                idlToSdfits_baseline_subtract = '0'

            if cl_params.keeptempfiles:
                keeptempfiles = '1'
            else:
                keeptempfiles = '0'

            aips_cmd = ' '.join((aipspy, load_script,
                                 aips_number,
                                 "--feeds", (','.join(feeds)),
                                 "--average", str(cl_params.average),
                                 "--channels", channels,
                                 "--display_idlToSdfits", display_idlToSdfits,
                                 "--idlToSdfits_rms_flag", idlToSdfits_rms_flag,
                                 "--verbose", str(cl_params.verbose),
                                 "--idlToSdfits_baseline_subtract", idlToSdfits_baseline_subtract,
                                 "--keeptempfiles", keeptempfiles,
                                 aipsinfiles))

            log.doMessage('DBG', aips_cmd)

            p = subprocess.Popen(aips_cmd.split(), stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            try:
                aips_stdout, aips_stderr = p.communicate()
            except:
                log.doMessage('ERR', aips_cmd, 'failed.')
                sys.exit()

            log.doMessage('DBG', aips_stdout)
            log.doMessage('DBG', aips_stderr)
            log.doMessage('INFO', '... (step 1 of 2) done')

            # define command to invoke mapping script
            # which in turn invokes AIPS via ParselTongue
            aips_cmd = ' '.join((aipspy, map_script, aips_number,
                                 '-u=_{0}_{1}'.format(str(thismap.start), str(thismap.end))))
            log.doMessage('DBG', aips_cmd)

            p = subprocess.Popen(aips_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            aips_stdout, aips_stderr = p.communicate()

            log.doMessage('DBG', aips_stdout)
            log.doMessage('DBG', aips_stderr)
            log.doMessage('INFO', '... (step 2 of 2) done')
