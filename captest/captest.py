# standard library imports
import os
import datetime
import re
import math
import copy
import collections
from functools import wraps
import warnings
import importlib

# anaconda distribution defaults
import dateutil
import numpy as np
import pandas as pd

# anaconda distribution defaults
# statistics and machine learning imports
import statsmodels.formula.api as smf
from scipy import stats
# from sklearn.covariance import EllipticEnvelope
import sklearn.covariance as sk_cv

# anaconda distribution defaults
# visualization library imports
import matplotlib.pyplot as plt
from bokeh.io import output_notebook, show
from bokeh.plotting import figure
from bokeh.palettes import Category10, Category20c, Category20b
from bokeh.layouts import gridplot
from bokeh.models import Legend, HoverTool, tools, ColumnDataSource

# visualization library imports
hv_spec = importlib.util.find_spec('holoviews')
if hv_spec is not None:
    import holoviews as hv
else:
    warnings.warn('Some plotting functions will not work without the '
                  'holoviews package.')

pvlib_spec = importlib.util.find_spec('pvlib')
if pvlib_spec is not None:
    from pvlib.clearsky import detect_clearsky
else:
    warnings.warn('Clear sky functions will not work without the '
                  'pvlib package.')

from captest.capdata import CapData, met_keys

# EllipticEnvelope gives warning about increasing determinate that prints
# out in a loop and does not seem to affect result of removing outliers.
warnings.filterwarnings(action='ignore', category=RuntimeWarning,
                        module='sklearn')


def equip_counts(df):
    """
    Returns list of integers that are a count of columns with the same name.

    Todo
    ----
    Recycle
        Determine if code might be useful somewhere.
    """
    equip_counts = {}
    eq_cnt_lst = []
    col_names = df.columns.tolist()
    for i, col_name in enumerate(col_names):
        # print('################')
        # print('loop: {}'.format(i))
        # print(col_name)
        if i == 0:
            equip_counts[col_name] = 1
            eq_cnt_lst.append(equip_counts[col_name])
            continue
        if col_name not in equip_counts.keys():
            equip_counts[col_name] = 1
            eq_cnt_lst.append(equip_counts[col_name])
        else:
            equip_counts[col_name] += 1
            eq_cnt_lst.append(equip_counts[col_name])
#         print(eq_cnt_lst[i])
    return eq_cnt_lst


class CapTest(object):
    """
    CapTest provides methods to facilitate solar PV capacity testing.

    The CapTest class provides a framework to facilitate visualizing, filtering,
    and performing regressions on data typically collected from operating solar
    pv plants or solar energy production models.

    The class parameters include an unmodified CapData object and filtered
    CapData object for both measured and simulated data.

    Parameters
    ----------
    das : CapData, required
        The CapData object containing data from a data acquisition system (das).
        This is the measured data used to perform a capacity test.
    flt_das : CapData
        A CapData object containing a filtered version of the das data.  Filter
        methods always modify this attribute or flt_sim.
    das_mindex : list of tuples
        Holds the row index data modified by the update_summary decorator
        function.
    das_summ_data : list of dicts
        Holds the data modifiedby the update_summary decorator function.
    sim : CapData, required
        Identical to das for data from an energy production simulation.
    flt_sim : CapData
        Identical to flt_das for data from an energy production simulation.
    sim_mindex : list of tuples
        Identical to das_mindex for data from an energy production simulation.
    sim_summ_data : list of dicts
        Identical to das_summ_data for data from an energy production simulation.
    rc : DataFrame
        Dataframe for the reporting conditions (poa, t_amb, and w_vel).
    ols_model_das : statsmodels linear regression model
        Holds the linear regression model object for the das data.
    ols_model_sim : statsmodels linear regression model
        Identical to ols_model_das for simulated data.
    reg_fml : str
        Regression formula to be fit to measured and simulated data.  Must
        follow the requirements of statsmodels use of patsy.
    """

    def __init__(self, das, sim):
        self.das = das
        self.flt_das = CapData()
        self.das_mindex = []
        self.das_summ_data = []
        self.sim = sim
        self.flt_sim = CapData()
        self.sim_mindex = []
        self.sim_summ_data = []
        self.rc = dict()
        self.ols_model_das = None
        self.ols_model_sim = None
        self.reg_fml = 'power ~ poa + I(poa * poa) + I(poa * t_amb) + I(poa * w_vel) - 1'
