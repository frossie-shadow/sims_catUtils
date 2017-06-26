"""
This script will validate the MBA tables on fatboy by querying a random
sample of asteroids and using the orbit propagation and ephemeride
generation code in sims_movingObjects to verify that the position parametrized
on fatboy is within 5 milliarcseconds of the position calculated directly by
pyoorb.

Running this script will require installing and setting up sims_movingObjects.

You will also need to compile the coordinate transformation code coordtrans.c
by running
    gcc -lm -o coord coordtrans.c
"""

from __future__ import with_statement
from subprocess import check_output

def equatorial_from_ecliptic(lon, lat):
    """
    Convert ecliptic coordinates to RA, Dec.
    Not vectorized; must do coordinate pairs one-at-a-time.

    Parameters:
    -----------
    lon is ecliptic longitude in degrees

    lat is ecliptic latitude in degrees

    Returns:
    -------
    RA in degrees

    Dec in degrees
    """

    try:
        result = check_output(["./coord", "-e", "%.6f" % lon, "%.6f" % lat])
    except OSError:
        print('\nTrying to call ./coord resulted in an exception\n'
              'Are you sure you have compiled coordtrans.c?\n'
              '    gcc -lm -o coord coordtrans.c\n')
        raise
    result = result.split('\n')
    ra_dec = result[1]
    ra_dec = ra_dec.split(':')[1]
    ra_dec = ra_dec.strip().split()
    return 15.0*float(ra_dec[0]), float(ra_dec[1])

import numpy as np
import os
import cStringIO
from lsst.sims.movingObjects import Orbits, PyOrbEphemerides
from lsst.sims.catUtils.baseCatalogModels import MBAObj
from lsst.sims.catalogs.db import DBObject
from lsst.sims.utils import ObservationMetaData
from lsst.sims.utils import _angularSeparation
from lsst.sims.utils import arcsecFromRadians

import time

def validate_orbits(obs, db, des_dir=None):
    """
    Take a telescope pointing, find all of the asteroids within that
    pointing, and validate the orbits as parametrized on fatboy against
    the orbits as directly evaluated by pyoorb

    Parameters
    ----------
    obs is an ObservationMetaData characterizing the telescope pointing

    db is a CatalogDBObject connecting to the Solar System object table
    we are currently validating

    des_dir is the directory containing the .des files with the original
    orbit paramters

    Returns
    -------
    The maximum difference between the position parametrized on fatboy
    and the position calculated by pyoorb in milliarcseconds.

    The number of objects tested.
    """

    if not hasattr(validate_orbits, 'ephemerides'):
        # construct a PyOrbEphemrides instantiation
        validate_orbits.ephemerides = PyOrbEphemerides()

    if not hasattr(validate_orbits, 'name_lookup'):
        # construct a lookup table associating objid with
        # the names of the objects as stored in the .des files
        dtype = np.dtype([('name', str, 8), ('id', int)])
        try:
            name_db = DBObject(database='LSSTSSM', host='fatboy.phys.washington.edu',
                               port=1433, driver='mssql+pymssql')
        except:
            name_db = DBObject(database='LSTSSM', host='localhost',
                               port=51433, driver='mssql+pymssql')

        query = 'SELECT name, ssmid from C14_mba_name_map'
        chunk_iter = name_db.get_arbitrary_chunk_iterator(query=query, dtype=dtype,
                                                          chunk_size=10000)

        validate_orbits.name_lookup = {}
        for chunk in chunk_iter:
            for line in chunk:
                validate_orbits.name_lookup[line['id']] = line['name']

        print 'built name look up dict'

    if not hasattr(validate_orbits, 'des_dir') or validate_orbits.des_dir != des_dir:
        # create a StringIO object containing all of the data from
        # the original .des files
        validate_orbits.des_dir = des_dir
        validate_orbits.des_cache = {}
        validate_orbits.header = None
        list_of_files = os.listdir(des_dir)
        first_file = True
        for file_name in list_of_files:
            if not file_name.endswith('.s3m'):
                continue
            with open(os.path.join(des_dir, file_name), 'r') as input_file:
                for ix, line in enumerate(input_file):
                    if ix==0:
                        if first_file:
                            validate_orbits.header = line
                            print 'read haeder from ',file_name
                            first_file = False
                        continue
                    split_line = line.strip().split()
                    validate_orbits.des_cache[split_line[0]] = line

    print 'finished initialization %d' % len(validate_orbits.des_cache)

    colnames = ['objid', 'raJ2000', 'decJ2000']

    results = db.query_columns(colnames=colnames, obs_metadata=obs,
                               chunk_size=100)

    t_start = time.time()
    max_displacement = -1.0
    n_obj = 0
    for chunk in results:
        n_obj += len(chunk)
        orbit_obj = Orbits()
        orbit_buffer = cStringIO.StringIO()
        orbit_buffer.write(validate_orbits.header)
        for asteroid in chunk:
            ast_name = validate_orbits.name_lookup[asteroid['objid']]
            orbit_buffer.write(validate_orbits.des_cache[ast_name])
        orbit_buffer.seek(0)
        orbit_obj.readOrbits(orbit_buffer)
        validate_orbits.ephemerides.setOrbits(orbit_obj)
        eph_list = validate_orbits.ephemerides.generateEphemerides(np.array([obs.mjd.UTC]), byObject=False)
        ra_vec = np.radians(np.array([rr for rr in eph_list['ra'][0]]))
        dec_vec = np.radians(np.array([dd for dd in eph_list['dec'][0]]))
        dd = 1000.0*arcsecFromRadians(_angularSeparation(chunk['raJ2000'], chunk['decJ2000'],
                                                         ra_vec, dec_vec))
        orbit_buffer.close()
        ellapsed = time.time()-t_start
        print 'local_max',dd.max(),max_displacement,ellapsed,ellapsed/n_obj
        if dd.max() > max_displacement:
            max_displacement = dd.max()

    return max_displacement, n_obj

if __name__ == "__main__":

    try:
        # if you are on UW campus/VPN
        mba_db = MBAObj(database='LSSTCATSIM', host='fatboy.phys.washington.edu',
                        port=1433, driver='mssql+pymssql')
    except:
        # if you need to use the SSH tunnel to connect to fatboy
        mba_db = MBAObj()

    ra, dec = equatorial_from_ecliptic(213.0, 1.1)

    obs = ObservationMetaData(mjd=60121.67,
                              pointingRA=ra,
                              pointingDec=dec,
                              boundLength=1.75,
                              boundType='circle')

    des_dir = os.path.join('/Users', 'danielsf', 'physics', 'lsst_150412',
                           'Development', 'garage', 'yusraNeoCode', 'data',
                           'raw')

    max_d, n_obj = validate_orbits(obs, mba_db, des_dir=des_dir)

    print max_d, n_obj
