"""
This script shows how to use our GalSim interface to generate FITS images of stars
"""

import os
import galsim
from lsst.sims.utils import radiansToArcsec
from lsst.sims.catalogs.measures.instance import InstanceCatalog
from lsst.sims.catalogs.generation.db import CatalogDBObject, ObservationMetaData
from lsst.sims.catUtils.baseCatalogModels import StarObj, OpSim3_61DBObject
from lsst.sims.catUtils.galSimInterface import ExampleOpticalPSF, GalSimStars

#if you want to use the actual LSST camera
#from lsst.obs.lsstSim import LsstSimMapper

class testGalSimStars(GalSimStars):
    #only draw images for u and g bands (for speed)
    band_pass_names = ['u','g']

    #defined in galSimInterface/galSimUtilities.py
    PSF = ExampleOpticalPSF()

#select an OpSim pointing
obsMD = OpSim3_61DBObject()
obs_metadata = obsMD.getObservationMetaData(88625744, 0.1, makeCircBounds = True)

#grab a database of galaxies (in this case, galaxy bulges)
stars = CatalogDBObject.from_objid('allstars')

#now append a bunch of objects with 2D sersic profiles to our output file
stars_galSim = testGalSimStars(stars, obs_metadata=obs_metadata)

#If you want to use the LSST camera, uncomment the line below.
#You can similarly assign any camera object you want here, as long
#as you do it before calling write_catalog()
#stars_galSim.camera = LsstSimMapper().camera

stars_galSim.write_catalog('galSim_star_example.txt', chunk_size=100)
stars_galSim.write_images(nameRoot='star')