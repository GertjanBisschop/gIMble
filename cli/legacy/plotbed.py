#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""usage: gimble plotbed       -b FILE [-o STR] [-h|--help]
                                            
    Options:
        -h --help                                   show this
        -b, --bed_file FILE                         BED file

"""

'''
[To Do]
- diagnostic plots
    - by_source
        - from bed
        - from zarr
    - by topic
        - distance
        - length
        - samples (in fifth column)
            - decay (shared in any)
            - sharedness as proportion of total (diagonal heatmap: https://seaborn.pydata.org/examples/many_pairwise_correlations.html)

- divide cli/lib code
'''

from timeit import default_timer as timer
from docopt import docopt
from tqdm import tqdm
#import lib.gimblelog
import lib.gimble
import numpy as np
import sys
import collections
import pandas as pd
import math
import matplotlib.pyplot as plt
import matplotlib as mat
mat.use("agg")

COLOR_HISTOGRAM = 'orange'
COLORS = ['deeppink', 'dodgerblue']
COLOR_AXES = 'grey'

LEGEND_FONTSIZE = 10
AXES_TICKS_FONTSIZE = 8
AXES_LABELS_FONTSIZE = 8

# MATPLOTLIB PARAMS
mat.rcParams['text.color'] = COLOR_AXES
mat.rcParams['axes.edgecolor'] = COLOR_AXES
mat.rcParams['xtick.color'] = COLOR_AXES
mat.rcParams['ytick.color'] = COLOR_AXES
mat.rcParams['grid.color'] = COLOR_AXES
mat.rcParams['font.family'] = 'sans-serif'
mat.rcParams['xtick.labelsize'] = AXES_LABELS_FONTSIZE
mat.rcParams['ytick.labelsize'] = AXES_LABELS_FONTSIZE
mat.rcParams['figure.frameon'] = False
mat.rcParams['axes.grid'] = False

def analyse_bed(parameterObj):
    print("[+] Parsing BED file...")
    try:
        bed_df = pd.read_csv(parameterObj.bed_file, sep="\t", usecols=[0,1,2], names=['sequence_id', 'start', 'end'], 
                                dtype={'sequence_id': str, 'start': 'Int64', 'end': 'Int64'}).sort_values(['sequence_id', 'start'], ascending=[True, True])
    except ValueError:
        sys.exit("[X] BED file %r does not contain the following the columns: 'sequence_id', 'start', 'end'" % (parameterObj.bed_file))
    count_sequences = bed_df['sequence_id'].nunique()
    count_intervals = len(bed_df.index)
    print("[+] Found %s BED intervals on %s sequences (%s intervals/sequence)..." % (
                                        lib.gimble.format_count(count_intervals), 
                                        lib.gimble.format_count(count_sequences), 
                                        lib.gimble.format_fraction(count_intervals / count_sequences)))
    bed_df['distance'] = np.where((bed_df['sequence_id'] == bed_df['sequence_id'].shift(-1)), (bed_df['start'].shift(-1) - bed_df['end']) + 1, np.nan)
    bed_df['length'] = (bed_df['end'] - bed_df['start'])
    
    distance_counter = collections.Counter(list(bed_df['distance'].dropna(how="any", inplace=False)))
    distance_scatter_f = parameterObj.bed_file.parent / (parameterObj.bed_file.stem + 'scatter.distance.png')
    distance_heatmap_f = parameterObj.bed_file.parent / (parameterObj.bed_file.stem + 'heatmap.distance.png')
    plot_heatmap(distance_counter, 'Distance to downstream BED interval', distance_heatmap_f)
    plot_loglog(distance_counter, 'Distance to downstream BED interval', distance_scatter_f)

    length_counter = collections.Counter(list(bed_df['length']))
    length_scatter_f = parameterObj.bed_file.parent / (parameterObj.bed_file.stem + 'scatter.length.png')
    length_heatmap_f = parameterObj.bed_file.parent / (parameterObj.bed_file.stem + 'heatmap.length.png')
    plot_heatmap(length_counter, 'Length of BED Intervals', length_heatmap_f)
    plot_loglog(length_counter, 'Length of BED intervals', length_scatter_f)

    #for sequence_id, df in bed_df.groupby('sequence_id'):
    #    distance_counter = collections.Counter(list(df['distance'].dropna(how="any", inplace=False)))
    #    distance_f = parameterObj.bed_file.parent / (parameterObj.bed_file.stem + '.%s.distance.png' % sequence_id)
    #    plot_distance(distance_f, distance_counter)

def plot_heatmap1(counter, xlabel, out_f):
    x = np.array(list(counter.keys()))
    y = np.array(list(counter.values()))
    MIN = 1
    MAX = 100000000
    #bins = 10 ** np.linspace(np.log10(MIN), np.log10(MAX), 50)
    y_space = np.linspace(x.min(), x.max(), num=49)
    x_space = np.geomspace(MIN, MAX, num=49)
    heatmap, xedges, yedges = np.histogram2d(x,y, bins=[x_space, y_space])
    fig = plt.figure(figsize=(12, 12), dpi=200, frameon=True)
    ax = fig.add_subplot(111)
    #heatmap = ax.pcolor((xedges, yedges), cmap=plt.cm.Blues, alpha=0.8)
    X,Y = np.meshgrid(xedges, yedges)
    ax.imshow(heatmap, interpolation='none', cmap=plt.cm.Blues, origin='lower')
    #xlabels = [item.get_text() for item in ax.get_xticklabels()]
    ax.set_xticklabels(xedges)
    ax.set_yticklabels(yedges)
    #ax.loglog()
    #ax.set_xlim(xedges[0], xedges[-1])
    #ax.set_ylim(yedges[0], yedges[-1])
    plt.xlabel(xlabel)
    fig.savefig(out_f, format="png")

def plot_heatmap(counter, xlabel, out_f):
    labels, values = zip(*counter.items())
    indexes = np.arange(len(labels))
    width = 1
    fig = plt.figure(figsize=(12, 12), dpi=200, frameon=True)
    ax = fig.add_subplot(111)
    ax.bar(indexes, values, width)
    #ax.xticks(indexes + width * 0.5, labels)
    fig.savefig(out_f, format="png")
    # #bins = 10 ** np.linspace(np.log10(MIN), np.log10(MAX), 50)
    # y_space = np.linspace(x.min(), x.max(), num=49)
    # x_space = np.geomspace(MIN, MAX, num=49)
    # heatmap, xedges, yedges = np.histogram2d(x,y, bins=[x_space, y_space])
    
    # #heatmap = ax.pcolor((xedges, yedges), cmap=plt.cm.Blues, alpha=0.8)
    # X,Y = np.meshgrid(xedges, yedges)
    # ax.imshow(heatmap, interpolation='none', cmap=plt.cm.Blues, origin='lower')
    # #xlabels = [item.get_text() for item in ax.get_xticklabels()]
    # ax.set_xticklabels(xedges)
    # ax.set_yticklabels(yedges)
    # #ax.loglog()
    # #ax.set_xlim(xedges[0], xedges[-1])
    # #ax.set_ylim(yedges[0], yedges[-1])
    # plt.xlabel(xlabel)
    # fig.savefig(out_f, format="png")

def plot_loglog(counter, xlabel, out_f):
    y_vals = []
    x_vals = []
    for idx, (value, count) in enumerate(counter.most_common()):
        x_vals.append(value)
        y_vals.append(count)
    fig = plt.figure(figsize=(16, 4), dpi=200, frameon=True)
    ax = fig.add_subplot(111)
    ax.axhline(1, color='lightgrey')
    ax.axvline(1, color='lightgrey')
    ax.plot(x_vals, y_vals, 'or', color='black', alpha=0.2, markersize=3)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    #plt.xlabel('Mutuples [%s]' % ",".join(MUTYPE_ORDER)) 
    plt.ylabel('Count')
    plt.xlabel(xlabel)
    plt.yscale('log')
    plt.xscale('log')
    plt.tight_layout()
    fig.savefig(out_f, format="png")
    print("[>] Created: %r" % str(out_f))
    plt.close(fig)

class PlotbedParameterObj(lib.gimble.ParameterObj):
    '''Sanitises command line arguments and stores parameters'''
    def __init__(self, params, args):
        super().__init__(params)
        self.bed_file = self._get_path(args['--bed_file'], path=True)

def main(params):
    try:
        start_time = timer()
        args = docopt(__doc__)
        #print(args)
        #log = lib.log.get_logger(run_params)
        parameterObj = PlotbedParameterObj(params, args)
        analyse_bed(parameterObj)
        print("[*] Total runtime: %.3fs" % (timer() - start_time))
    except KeyboardInterrupt:
        print("\n[X] Interrupted by user after %s seconds!\n" % (timer() - start_time))
        sys.exit(-1)
