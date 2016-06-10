from __future__ import print_function
import numpy as np

from lsst.sims.catalogs.measures.instance import compound
from lsst.sims.catUtils.mixins import SNIaCatalog, PhotometryBase
from lsst.sims.catUtils.utils import _baseLightCurveCatalog
from lsst.sims.catUtils.utils import LightCurveGenerator

from lsst.sims.catUtils.supernovae import SNObject, SNUniverse
from lsst.sims.photUtils import PhotometricParameters, calcGamma
from lsst.sims.photUtils import Sed, calcMagError_m5

__all__ = ["SNIaLightCurveGenerator"]



class _sniaLightCurveCatalog(_baseLightCurveCatalog, SNIaCatalog, PhotometryBase):

    column_outputs = ["uniqueId", "snid", "raJ2000", "decJ2000",
                      "cosmologicalDistanceModulus", "redshift", "EBV"]

    _suppressDimSN = False


class SNIaLightCurveGenerator(LightCurveGenerator):

    def __init__(self, *args, **kwargs):
        self._lightCurveCatalogClass = _sniaLightCurveCatalog
        self._filter_cat = None
        self._ax_cache = None
        self._bx_cache = None
        self._ax_bx_wavelen = None
        self.phot_params = PhotometricParameters()
        self.sn_universe = SNUniverse()
        self.sn_universe.suppressDimSN = False
        super(SNIaLightCurveGenerator, self).__init__(*args, **kwargs)


    class _filterCatalogClass(_sniaLightCurveCatalog):
        column_outputs = ["uniqueId", "t0"]


    def _light_curves_from_query(self, cat, query_result, grp):

        bandpass = cat.lsstBandpassDict[grp[0].bandpass]

        t_list = np.array([obs.mjd.TAI for obs in grp])

        gamma_list = np.array([calcGamma(bandpass, obs.m5[obs.bandpass], self.phot_params)
                               for obs in grp])

        snobj = SNObject()

        for chunk in query_result:
            for sn in cat.iter_catalog(query_cache=[chunk]):
                sn_rng = self.sn_universe.getSN_rng(sn[1])
                sn_t0 = self.sn_universe.drawFromT0Dist(sn_rng)
                if np.isfinite(sn_t0) and \
                sn_t0<t_list[-1]+cat.maxTimeSNVisible and \
                sn_t0>t_list[0]-cat.maxTimeSNVisible:

                    sn_c = self.sn_universe.drawFromcDist(sn_rng)
                    sn_x1 = self.sn_universe.drawFromx1Dist(sn_rng)
                    sn_x0 = self.sn_universe.drawFromX0Dist(sn_rng, sn_x1, sn_c, sn[4])

                    snobj.set(t0=sn_t0, c=sn_c, x1=sn_x1, x0=sn_x0, z=sn[5])

                    if snobj.maxtime()>=t_list[0] and snobj.mintime()<=t_list[-1]:
                        active_dexes = np.where(np.logical_and(t_list>=snobj.mintime(),
                                                               t_list<=snobj.maxtime()))

                        t_active = t_list[active_dexes]
                        m5_active = np.array([obs.m5[obs.bandpass] for obs in grp])[active_dexes]
                        gamma_active = gamma_list[active_dexes]

                        if len(t_active)>0:
                            wave_ang = bandpass.wavelen * 10.0
                            mask = np.logical_and(wave_ang>snobj.minwave(),
                                                  wave_ang<snobj.maxwave())
                            wave_ang = wave_ang[mask]
                            flambda_grid = snobj.flux(time=t_active, wave=wave_ang)*10.0

                            flambda = np.zeros(len(bandpass.wavelen))*np.nan
                            mag_list = []
                            for ix, ff in enumerate(flambda_grid):
                                flambda[mask] = ff
                                flambda = np.where(flambda > 0., flambda, 0.)
                                ss = Sed(wavelen=bandpass.wavelen, flambda=flambda)

                                if self._ax_bx_wavelen is None or \
                                len(self._ax_bx_wavelen) != len(bandpass.wavelen) or \
                                (self._ax_bx_wavelen!=bandpass.wavelen).any():

                                    self._ax_bx_wavelen = bandpass.wavelen
                                    self._ax_cache, self._bx_cache = ss.setupCCMab()

                                ss.addCCMDust(a_x=self._ax_cache, b_x=self._bx_cache, ebv=sn[6])
                                flux = ss.calcFlux(bandpass)
                                mag = ss.magFromFlux(flux)
                                mag_list.append(mag)

                            mag_list = np.array(mag_list)

                            acceptable = np.where(np.isfinite(mag_list))
                            mag_error_list = calcMagError_m5(mag_list[acceptable], bandpass,
                                                             m5_active[acceptable], self.phot_params,
                                                             gamma=gamma_active[acceptable])

                            if sn[0] not in self.mjd_dict:
                                self.mjd_dict[sn[0]] = []
                                self.mag_dict[sn[0]] = []
                                self.sig_dict[sn[0]] = []

                            for tt, mm, ee in zip(t_active[acceptable], mag_list[acceptable],
                                                  mag_error_list[0]):

                                self.mjd_dict[sn[0]].append(tt)
                                self.mag_dict[sn[0]].append(mm)
                                self.sig_dict[sn[0]].append(ee)