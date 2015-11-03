from __future__ import with_statement
import os
import numpy as np
import unittest
import lsst.utils.tests as utilsTests

from lsst.utils import getPackageDir
from lsst.sims.catalogs.generation.db import fileDBObject
from lsst.sims.utils import ObservationMetaData
from lsst.sims.catalogs.measures.instance import InstanceCatalog, compound
from lsst.sims.catUtils.mixins import PhotometryStars, PhotometryGalaxies
from lsst.sims.photUtils import BandpassDict, Bandpass, Sed, PhotometricParameters, calcMagError_m5

class CartoonStars(InstanceCatalog, PhotometryStars):
    column_outputs = ['cartoon_u', 'cartoon_g',
                      'sigma_cartoon_u', 'sigma_cartoon_g']

    default_formats = {'f': '%.13f'}


    @compound('cartoon_u', 'cartoon_g')
    def get_cartoon_mags(self):
        if not hasattr(self, 'cartoonBandpassDict'):
            self.cartoonBandpassDict = BandpassDict.loadTotalBandpassesFromFiles(
                                                     bandpassNames = ['u', 'g'],
                                                     bandpassDir = os.path.join(getPackageDir('sims_photUtils'), 'tests',
                                                                               'cartoonSedTestData'),
                                                     bandpassRoot = 'test_bandpass_'
                                                     )

        return self._magnitudeGetter(self.cartoonBandpassDict, self.get_cartoon_mags._colnames)


    @compound('sigma_cartoon_u', 'sigma_cartoon_g')
    def get_cartoon_uncertainty(self):
        return self._magnitudeUncertaintyGetter(['cartoon_u', 'cartoon_g'], 'cartoonBandpassDict')


class CartoonUncertaintyTestCase(unittest.TestCase):
    """
    This unit test suite will verify that our 'arbitrarily extensible' framework
    for writing magnitude uncertainty getters actually behaves as advertised
    """

    def setUp(self):
        self.normband = Bandpass()
        self.normband.imsimBandpass()
        self.uband = Bandpass()
        self.uband.readThroughput(os.path.join(getPackageDir('sims_photUtils'), 'tests', 'cartoonSedTestData', 'test_bandpass_u.dat'))
        self.gband = Bandpass()
        self.gband.readThroughput(os.path.join(getPackageDir('sims_photUtils'), 'tests', 'cartoonSedTestData', 'test_bandpass_g.dat'))

    def test_stars(self):
        obs = ObservationMetaData(bandpassName=['u', 'g'],
                                  m5=[25.0, 26.0])
        db_dtype = np.dtype([
                           ('id', np.int),
                           ('raJ2000', np.float),
                           ('decJ2000', np.float),
                           ('sedFilename', str, 100),
                           ('magNorm', np.float),
                           ('galacticAv', np.float)
                           ])

        inputDir = os.path.join(getPackageDir('sims_catUtils'), 'tests', 'testData')
        inputFile = os.path.join(inputDir, 'IndicesTestCatalogStars.txt')
        db = fileDBObject(inputFile, dtype=db_dtype, runtable='test', idColKey='id')
        catName = os.path.join(getPackageDir('sims_catUtils'), 'tests', 'scratchSpace', 'cartoonStarCat.txt')
        cat = CartoonStars(db, obs_metadata=obs)
        cat.write_catalog(catName)

        dtype = np.dtype([(name, np.float) for name in cat.column_outputs])

        controlData = np.genfromtxt(catName, dtype=dtype, delimiter=',')

        if os.path.exists(catName):
            os.unlink(catName)

        db_columns = db.query_columns(['id', 'raJ2000', 'decJ2000', 'sedFilename', 'magNorm', 'galacticAv'])

        sedDir = os.path.join(getPackageDir('sims_sed_library'), 'starSED', 'kurucz')

        for ix, line in enumerate(db_columns.next()):
            spectrum = Sed()
            spectrum.readSED_flambda(os.path.join(sedDir, line[3]))
            fnorm = spectrum.calcFluxNorm(line[4], self.normband)
            spectrum.multiplyFluxNorm(fnorm)
            a_x, b_x = spectrum.setupCCMab()
            spectrum.addCCMDust(a_x, b_x, A_v=line[5])
            umag = spectrum.calcMag(self.uband)
            self.assertAlmostEqual(umag, controlData['cartoon_u'][ix], 10)
            gmag = spectrum.calcMag(self.gband)
            self.assertAlmostEqual(gmag, controlData['cartoon_g'][ix], 10)
            magError = calcMagError_m5(np.array([umag, gmag]), [self.uband, self.gband], [obs.m5['u'], obs.m5['g']], PhotometricParameters())
            self.assertAlmostEqual(magError[0], controlData['sigma_cartoon_u'][ix], 10)
            self.assertAlmostEqual(magError[1], controlData['sigma_cartoon_g'][ix], 10)


def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(CartoonUncertaintyTestCase)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    utilsTests.run(suite(),shouldExit)

if __name__ == "__main__":
    run(True)