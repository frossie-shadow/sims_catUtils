"""
The class SNObj is a catalogDB class which can read a table of SALT2
parameters on the catsim database
"""
from .BaseCatalogModels import BaseCatalogObj
from lsst.sims.utils import ObservationMetaData

__all__ = ['SNDBObj'] 

class SNDBObj(BaseCatalogObj):
    objid = 'TwinkUnlensedSN'
    # From now on the tableid should be specified in instantiating the class
    # table = 'TwinkSN' or 'TwinkSNKraken'
    idColKey = 'id'
    raColName = 'snra'
    decColName = 'sndec'
    objectTypeId = 42
    #Don't run test on base class
    doRunTest = False
    #default observation metadata
    testObservationMetaData = ObservationMetaData(boundType='circle',
                                                  pointingRA=53.125,
                                                  pointingDec=-27.9,
                                                  boundLength=0.1,
                                                  mjd=52000.,
                                                  bandpassName='r',
                                                  m5=22.0)
    
    dbDefaultValues = {'varsimobjid':-1, 'runid':-1, 'ismultiple':-1, 'run':-1,
                       'runobjid':-1}

    # These types should be matched to the database.
    #: Default map is float.  If the column mapping is the same as the
    # column name, None can be specified

    columns = [('raJ2000', 'snra*PI()/180.'),
               ('decJ2000', 'sndec*PI()/180.'),
               ('Tt0', 't0'),
               ('Tx0', 'x0'),
               ('Tx1', 'x1'),
               ('Tc', 'c'),
               ('Tsnid', 'id'),
               ('Tredshift', 'redshift'),
               ('Tgaltileid', 'galtileid')
              ]
