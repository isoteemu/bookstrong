#!/usr/bin/env python3
r'''
==================================
Kalman Filter tracking a sine wave
==================================
This example shows how to use the Kalman Filter for state estimation.
In this example, we generate a fake target trajectory using a sine wave.
Instead of observing those positions exactly, we observe the position plus some
random noise.  We then use a Kalman Filter to estimate the velocity of the
system as well.
The figure drawn illustrates the observations, and the position and velocity
estimates predicted by the Kalman Smoother.
'''

import numpy as np
import pylab as pl

from pykalman import KalmanFilter

import plotly.plotly as py
from plotly.graph_objs import *

from sqlalchemy import func

import pandas as pd

from datetime import date, datetime
from dateutil.parser import parse

from . import BASE_SCORE

def kalmafy(matches):

	means = matches.resample('D', how='mean')

	observations_missing = np.ma.array(
		means.get_values(),
		mask=np.zeros(means.shape)
	)

	for i, weekly in enumerate(observations_missing):
		if pd.isnull(weekly):
			observations_missing[i] = np.ma.masked

	smoothed = kalman_smooth(observations_missing)

	return pd.Series(index=matches.index, data=smoothed)


def kalman_smooth(observations, **kwargs):
	'''
		Smooth shit
	'''
	kwargs.setdefault('initial_state_mean', BASE_SCORE)
	kwargs.setdefault('transition_covariance', 0.01 * np.eye(1))

	kf = KalmanFilter(**kwargs)

	states_pred = kf.smooth(observations)[0]

	return states_pred[:, 0]
