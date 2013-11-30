"""
Does a broad, general test of the parallel.multiprocessing.mpi functionality. 

Uses 2 prcesses since we can be reasonably sure that the users computer will
at least have 2 cores.

Note: This module has to re-spawn itself using mpirun so standby for something 
very boggly.

Generates a pair of images, and then applies a function to calculate
the average of them. Checks the resulting output against a known 
correct answer. 

Steals heavily from testavg
"""
# This file is part of RIOS - Raster I/O Simplification
# Copyright (C) 2012  Sam Gillingham, Neil Flood
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import sys
import subprocess
import numpy
from osgeo import gdal
from rios.parallel.mpi import applier

TESTNAME = "TESTAVGMPI"

TEST_NCPUS = 2
MPIRUN = 'mpirun'

import riostestutils

def run():
    """
    Run the test
    """
    riostestutils.reportStart(TESTNAME)
    
    ramp1 = 'ramp1.img'
    ramp2 = 'ramp2.img'
    riostestutils.genRampImageFile(ramp1)
    riostestutils.genRampImageFile(ramp2, reverse=True)
    outfile = 'rampavg.img'

    # assume this is in the same dir as testrios.py
    # and execute this script with mpirun passing
    # in the filenames
    appDir = os.path.dirname(os.path.abspath(sys.argv[0]))
    thisScript = os.path.join(appDir, 'testavgmpi.py')
    args = [MPIRUN, '-n', str(TEST_NCPUS), 'python', thisScript,
            ramp1, ramp2, outfile]
    try:
        retCode = subprocess.call(args)
        
        if retCode != 0:
            print("Received error code %d from mpirun" % retCode)
            print("Failed to execute mpirun")
            ok = False

        else:
            ok = checkResult(outfile)
    except FileNotFoundError as e:
        print(e)
        ok = False
    
    # Clean up
    for filename in [ramp1, ramp2, outfile]:
        if os.path.exists(filename):
            os.remove(filename)
    
    return ok

def calcAverage(file1, file2, avgfile):
    """
    Use RIOS to calculate the average of two files.

    called from the '__name__ == "__main__"' clause below
    when this is executed from mpirun.
    Will be called TEST_NCPUS times - one per spawned process
    """
    infiles = applier.FilenameAssociations()
    outfiles = applier.FilenameAssociations()
    infiles.img = [file1, file2]
    outfiles.avg = avgfile

    applier.apply(doAvg, infiles, outfiles)


def doAvg(info, inputs, outputs):
    """
    Called from RIOS.
    
    Calculate the average of the input files. 
    
    """
    tot = inputs.img[0].astype(numpy.float32)
    for img in inputs.img[1:]:
        tot += img
    outputs.avg = (tot / len(inputs.img)).astype(numpy.uint8)


def checkResult(avgfile):
    """
    Read in from the given file, and check that it matches what we 
    think it should be
    """
    # Work out the correct answer
    ramp1 = riostestutils.genRampArray()
    ramp2 = riostestutils.genRampArray()[:, ::-1]
    tot = (ramp1.astype(numpy.float32) + ramp2)
    avg = (tot / 2.0).astype(numpy.uint8)
    
    # Read what RIOS wrote
    ds = gdal.Open(avgfile)
    band = ds.GetRasterBand(1)
    riosavg = band.ReadAsArray()
    del ds
    
    # Check that they are the same
    ok = True
    if avg.shape != riosavg.shape:
        riostestutils.report(TESTNAME, "Shape mis-match: %s != %s"%(avg.shape, riosavg.shape))
        ok = False
    elif (riosavg-avg).any():
        riostestutils.report(TESTNAME, "Incorrect result. Average difference = %s"%(riosavg-avg).mean())
        ok = False
    else:
        riostestutils.report(TESTNAME, "Passed")

    return ok

if __name__ == "__main__":
    # assume we are being called from mpirun
    # interpret the command line args and call
    # calcAverage()
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    outfile = sys.argv[3]
    calcAverage(file1, file2, outfile)

