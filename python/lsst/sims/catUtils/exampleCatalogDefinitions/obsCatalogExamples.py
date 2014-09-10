"""Instance Catalog"""
import numpy
import eups
from lsst.sims.catalogs.measures.instance import InstanceCatalog
from lsst.sims.coordUtils.Astrometry import AstrometryStars, CameraCoords
from lsst.sims.photUtils.Photometry import PhotometryStars
from lsst.obs.lsstSim.utils import loadCamera

class ObsStarCatalogBase(InstanceCatalog, AstrometryStars, PhotometryStars, CameraCoords):
    comment_char = ''
    camera = loadCamera(eups.productDir('obs_lsstSim'))
    catalog_type = 'obs_star_cat'
    column_outputs = ['uniqueId', 'raObserved', 'decObserved', 'lsst_u', 'sigma_lsst_u', 
                      'lsst_g', 'sigma_lsst_g', 'lsst_r', 'sigma_lsst_r', 'lsst_i', 
                      'sigma_lsst_i', 'lsst_z', 'sigma_lsst_z', 'lsst_y', 'sigma_lsst_y',
                      'chipName', 'xPix', 'yPix']
    default_formats = {'S':'%s', 'f':'%.8f', 'i':'%i'}
    transformations = {'raObserved':numpy.degrees, 'decObserved':numpy.degrees}