import unittest
import os
import numpy as np

import lsst.utils.tests
from lsst.utils import getPackageDir

from lsst.sims.utils import _angularSeparation
from lsst.sims.utils import angularSeparation
from lsst.sims.utils import arcsecFromRadians
from lsst.sims.catalogs.definitions import InstanceCatalog
from lsst.sims.catUtils.utils import makePhoSimTestDB
from lsst.sims.catUtils.utils import testStarsDBObj, testGalaxyDiskDBObj
from lsst.sims.catUtils.mixins import PhoSimAstrometryBase
from lsst.sims.catUtils.mixins import PhoSimAstrometryStars
from lsst.sims.catUtils.mixins import PhoSimAstrometryGalaxies
from lsst.sims.utils.CodeUtilities import sims_clean_up

def setup_module(module):
    lsst.utils.tests.init()


class StarTestCatalog(PhoSimAstrometryStars, InstanceCatalog):
    column_outputs = ['raICRS', 'decICRS', 'raPhoSim', 'decPhoSim']
    transformations = {'raICRS': np.degrees, 'decICRS': np.degrees,
                       'raPhoSim': np.degrees, 'decPhoSim': np.degrees}

    override_formats = {'raICRS': '%.12g', 'decICRS': '%.12g',
                        'raPhoSim': '%.12g', 'decPhoSim': '%.12g'}

    delimiter = ' '


class GalaxyTestCatalog(PhoSimAstrometryGalaxies, InstanceCatalog):
    column_outputs = ['raICRS', 'decICRS', 'raPhoSim', 'decPhoSim']
    transformations = {'raICRS': np.degrees, 'decICRS': np.degrees,
                       'raPhoSim': np.degrees, 'decPhoSim': np.degrees}

    override_formats = {'raICRS': '%.12g', 'decICRS': '%.12g',
                        'raPhoSim': '%.12g', 'decPhoSim': '%.12g'}

    delimiter = ' '


class PhoSimAstrometryTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.scratch_dir = os.path.join(getPackageDir('sims_catUtils'),
                                       'tests', 'scratchSpace')
        cls.db_name = os.path.join(cls.scratch_dir, 'PhoSimAstDB.db')
        if os.path.exists(cls.db_name):
            os.unlink(cls.db_name)
        cls.obs = makePhoSimTestDB(filename=cls.db_name,
                                   size=1000)

    @classmethod
    def tearDownClass(cls):
        sims_clean_up()
        if os.path.exists(cls.db_name):
            os.unlink(cls.db_name)

    def test_stellar_astrometry_radians(self):
        """
        Test that we can go from raPhoSim, decPhoSim to ICRS coordinates
        in the case of stars (in radians)
        """
        cat_name = os.path.join(self.scratch_dir, 'phosim_ast_star_cat_rad.txt')
        if os.path.exists(cat_name):
            os.unlink(cat_name)

        db = testStarsDBObj(driver='sqlite', database=self.db_name)
        cat = StarTestCatalog(db, obs_metadata=self.obs)
        cat.write_catalog(cat_name)
        dtype = np.dtype([('raICRS', float), ('decICRS', float),
                          ('raPhoSim', float), ('decPhoSim', float)])
        data = np.genfromtxt(cat_name, dtype=dtype)
        self.assertGreater(len(data), 100)
        ra_pho_rad = np.radians(data['raPhoSim'])
        dec_pho_rad = np.radians(data['decPhoSim'])

        # verify that, when transforming back to ICRS, we are within
        # 10^-3 arcsec
        ra_icrs, dec_icrs = PhoSimAstrometryBase._icrsFromPhoSim(ra_pho_rad,
                                                                 dec_pho_rad,
                                                                 self.obs)
        dist = _angularSeparation(np.radians(data['raICRS']),
                                  np.radians(data['decICRS']),
                                  ra_icrs, dec_icrs)

        dist = arcsecFromRadians(dist)
        self.assertLess(dist.max(), 0.001)

        # verify that the distance between raPhoSim, decPhoSim and
        # raICRS, decICRS is greater than the distance between
        # the original raICRS, decICRS and the newly-calculated
        # raICRS, decICRS
        dist_bad = _angularSeparation(ra_pho_rad, dec_pho_rad,
                                      np.radians(data['raICRS']),
                                      np.radians(data['decICRS']))

        dist_bad = arcsecFromRadians(dist_bad)
        self.assertGreater(dist_bad.min(), dist.max())

        if os.path.exists(cat_name):
            os.unlink(cat_name)
        del db

    def test_stellar_astrometry_degrees(self):
        """
        Test that we can go from raPhoSim, decPhoSim to ICRS coordinates
        in the case of stars (in degrees)
        """
        cat_name = os.path.join(self.scratch_dir, 'phosim_ast_star_cat_deg.txt')
        if os.path.exists(cat_name):
            os.unlink(cat_name)

        db = testStarsDBObj(driver='sqlite', database=self.db_name)
        cat = StarTestCatalog(db, obs_metadata=self.obs)
        cat.write_catalog(cat_name)
        dtype = np.dtype([('raICRS', float), ('decICRS', float),
                          ('raPhoSim', float), ('decPhoSim', float)])
        data = np.genfromtxt(cat_name, dtype=dtype)
        self.assertGreater(len(data), 100)

        # verify that, when transforming back to ICRS, we are within
        # 10^-3 arcsec
        ra_icrs, dec_icrs = PhoSimAstrometryBase.icrsFromPhoSim(data['raPhoSim'],
                                                                data['decPhoSim'],
                                                                self.obs)
        dist = angularSeparation(data['raICRS'], data['decICRS'],
                                 ra_icrs, dec_icrs)

        dist = 3600.0*dist
        self.assertLess(dist.max(), 0.001)

        # verify that the distance between raPhoSim, decPhoSim and
        # raICRS, decICRS is greater than the distance between
        # the original raICRS, decICRS and the newly-calculated
        # raICRS, decICRS
        dist_bad = angularSeparation(data['raPhoSim'], data['decPhoSim'],
                                     data['raICRS'], data['decICRS'])

        dist_bad = 3600.0*dist_bad
        self.assertGreater(dist_bad.min(), dist.max())

        if os.path.exists(cat_name):
            os.unlink(cat_name)
        del db

    def test_galaxy_astrometry_radians(self):
        """
        Test that we can go from raPhoSim, decPhoSim to ICRS coordinates
        in the case of galaxies (in radians)
        """
        cat_name = os.path.join(self.scratch_dir, 'phosim_ast_gal_cat_rad.txt')
        if os.path.exists(cat_name):
            os.unlink(cat_name)

        db = testGalaxyDiskDBObj(driver='sqlite', database=self.db_name)
        cat = GalaxyTestCatalog(db, obs_metadata=self.obs)
        cat.write_catalog(cat_name)
        dtype = np.dtype([('raICRS', float), ('decICRS', float),
                          ('raPhoSim', float), ('decPhoSim', float)])
        data = np.genfromtxt(cat_name, dtype=dtype)
        self.assertGreater(len(data), 100)
        ra_pho_rad = np.radians(data['raPhoSim'])
        dec_pho_rad = np.radians(data['decPhoSim'])

        # verify that, when transforming back to ICRS, we are within
        # 10^-3 arcsec
        ra_icrs, dec_icrs = PhoSimAstrometryBase._icrsFromPhoSim(ra_pho_rad,
                                                                 dec_pho_rad,
                                                                 self.obs)
        dist = _angularSeparation(np.radians(data['raICRS']),
                                  np.radians(data['decICRS']),
                                  ra_icrs, dec_icrs)

        dist = arcsecFromRadians(dist)
        self.assertLess(dist.max(), 0.001)

        # verify that the distance between raPhoSim, decPhoSim and
        # raICRS, decICRS is greater than the distance between
        # the original raICRS, decICRS and the newly-calculated
        # raICRS, decICRS
        dist_bad = _angularSeparation(ra_pho_rad, dec_pho_rad,
                                      np.radians(data['raICRS']),
                                      np.radians(data['decICRS']))

        dist_bad = arcsecFromRadians(dist_bad)
        self.assertGreater(dist_bad.min(), dist.max())

        if os.path.exists(cat_name):
            os.unlink(cat_name)
        del db

    def test_galaxy_astrometry_degrees(self):
        """
        Test that we can go from raPhoSim, decPhoSim to ICRS coordinates
        in the case of galaxies (in degrees)
        """
        cat_name = os.path.join(self.scratch_dir, 'phosim_ast_gal_cat_deg.txt')
        if os.path.exists(cat_name):
            os.unlink(cat_name)

        db = testGalaxyDiskDBObj(driver='sqlite', database=self.db_name)
        cat = GalaxyTestCatalog(db, obs_metadata=self.obs)
        cat.write_catalog(cat_name)
        dtype = np.dtype([('raICRS', float), ('decICRS', float),
                          ('raPhoSim', float), ('decPhoSim', float)])
        data = np.genfromtxt(cat_name, dtype=dtype)
        self.assertGreater(len(data), 100)

        # verify that, when transforming back to ICRS, we are within
        # 10^-3 arcsec
        ra_icrs, dec_icrs = PhoSimAstrometryBase.icrsFromPhoSim(data['raPhoSim'],
                                                                data['decPhoSim'],
                                                                self.obs)
        dist = angularSeparation(data['raICRS'], data['decICRS'],
                                 ra_icrs, dec_icrs)

        dist = 3600.0*dist
        self.assertLess(dist.max(), 0.001)

        # verify that the distance between raPhoSim, decPhoSim and
        # raICRS, decICRS is greater than the distance between
        # the original raICRS, decICRS and the newly-calculated
        # raICRS, decICRS
        dist_bad = angularSeparation(data['raPhoSim'], data['decPhoSim'],
                                     data['raICRS'], data['decICRS'])

        dist_bad = 3600.0*dist_bad
        self.assertGreater(dist_bad.min(), dist.max())

        if os.path.exists(cat_name):
            os.unlink(cat_name)
        del db


class MemoryTestClass(lsst.utils.tests.MemoryTestCase):
    pass


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
