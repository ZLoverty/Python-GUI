# Define some utility functions that are used in 'Correlation' notebooks
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from myImageLib import dirrec, bestcolor, wowcolor
from scipy.ndimage import gaussian_filter1d, uniform_filter1d
from scipy.signal import savgol_filter, medfilt
from scipy.optimize import curve_fit
import corrLib
import os




# fig-2_GNF

def postprocess_gnf(gnf_data, lb, xlim=None, sparse=3):
    """
    Postprocess raw GNF data for plotting.
    
    Args:
    gnf_data -- DataFrame containing columns ('n', 'd'), generated by df2_nobp.py
    lb -- size of bacteria (pixel, normalizing factor of x axis)
    xlim -- box size beyond which the data get cut off (pixel), can be either integer or a list of 2 integers
            if xlim is int, it is the upper limit, data above xlim will be cut off,
            if xlim is a list, data outside [xlim[0], xlim[1]] will be cut off
    sparse -- the degree to sparsify the data, 1 is doing nothing, 3 means only keep 1/3 of the orginal data
    
    Returns:
    x, y -- a tuple that can be plotted directly using plt.plot(x, y)
    """    
    
    if xlim == None:
        data = gnf_data
    elif isinstance(xlim, int):
        data = gnf_data.loc[gnf_data.n < xlim*lb**2]
    elif isinstance(xlim, list) and len(xlim) == 2:
        data = gnf_data.loc[(gnf_data.n>=xlim[0]*lb**2)&(gnf_data.n < xlim[1]*lb**2)]
        
    xx = data.n / lb**2
    yy = data.d / data.n**0.5
    yy = yy / yy.iat[0]
    
    # sparcify
    x = xx[0:len(xx):sparse]
    y = yy[0:len(xx):sparse]
    
    return x, y

def collapse_data(gnf_data_tuple, lb, xlim=None, sparse=3):
    """
    Args:
    gnf_data_tuple -- a tuple of gnf_data (dataframe) generated by df2_nobp.py, it has to be a tuple
    lb -- size of bacteria (pixel, normalizing factor of x axis)
    xlim -- box size beyond which the data get cut off (pixel), can be either integer or a list of 2 integers
            if xlim is int, it is the upper limit, data above xlim will be cut off,
            if xlim is a list, data outside [xlim[0], xlim[1]] will be cut off
    sparse -- the degree to sparsify the data, 1 is doing nothing, 3 means only keep 1/3 of the orginal data
    
    Returns:
    collapsed -- DataFrame containing ('x', 'avg', 'std')    
        'x' -- l**2/lb**2 used for plotting GNF, index
        'avg' -- average values of given dataset (gnf_data_tuple)
        'err' -- standard deviation of given dataset
    """
    
    L = len(gnf_data_tuple)
    for i in range(0, L):
        x, y = postprocess_gnf(gnf_data_tuple[i], lb, xlim=xlim, sparse=sparse)
        data = pd.DataFrame(data={'x': x, 'y': y}).set_index('x')
        if i == 0:
            data_merge = data
        else:
            data_merge = data_merge.join(data, rsuffix=str(i))
            
    x = data_merge.index                
    avg = data_merge.mean(axis=1)
    std = data_merge.std(axis=1)
    
    collapsed = pd.DataFrame(data={'x': x, 'avg': avg, 'std': std}).set_index('x')
    
    return collapsed

def prepare_multiple_data(dirs):
    """
    Args:
    dirs -- a list of directories of GNF data
    
    Returns:
    gnf_data_tuple -- a tuple of GNF DataFrame ('n', 'd')
    """
    
    data_list = []
    
    for d in dirs:
        data_list.append(pd.read_csv(d))
        
    gnf_data_tuple = tuple(data_list)
    
    return gnf_data_tuple

def plot_predictions(ax, key='M19'):
    """
    Plot predictions from theory and simulations along with my data in ax. 
    2D predictions will be '--', 3D predictions will be '.-'. 
    
    Args:
    ax -- axis where I plot my data
    key -- the prediction to plot, can be 'TT95', 'R03' or 'M19', default to 'M19'
    Returns:
    None    
    """
    
    pred = {'TT95': (0.3, 0.27),
           'R03': (0.5, 0.33),
           'M19': (0.33, 0.3)}
    
    x = np.array(ax.get_xlim())
    y2d = pred[key][0] * np.ones(2)
    y3d = pred[key][1] * np.ones(2)
    
    ax.plot(x, y2d, color='black', ls='--', lw=0.5)
    ax.plot(x, y3d, color='black', ls='-.', lw=0.5)
    
    return None

def plot_std(k_data, seg_length, tlim=None, xlim=None, lb=10, mpp=0.33, fps=10, num_curves=5):
    """
    Args:
    k_data -- kinetics data computed by df2_kinetics.py, has 3 columns (n, d, segment)
    seg_length -- segment length [frame] used in computing kinetics
    tlim -- bounds of time, only plot the data in the bounds (second)
            tlim can be None, int or list of 2 int
                None - plot all t
                int - plot all below tlim
                list - plot between tlim[0] and tlim[1]
    xlim -- box size beyond which the data get cut off (pixel), can be either integer or a list of 2 integers
    lb -- size of single bacterium [px]
    mpp -- microns per pixel
    fps -- frames per second
    num_curve -- number of curves in the final plot
    
    Returns:
    plot_data -- a dict containing (x, y)'s of all the curved plotted
                example {'l1': (x1, y1), 'l2': (x2, y2)} 
                where x1, y1, x2, y2 are all array-like object
    fig -- the figure handle of the plot, use for saving the figure
    """
    
    symbol_list = [ 'x', 's', 'P', '*', 'd', 'o', '^']
    
    plot_data = {}
    
    # filter out the data we don't need using tlim
    if tlim == None:
        data = k_data
    elif isinstance(tlim, int):
        data = k_data.loc[(k_data.segment-1) * seg_length < tlim * fps]
    elif isinstance(tlim, list) and len(tlim) == 2:
        data = k_data.loc[((k_data.segment-1) * seg_length < tlim[1] * fps) & ((k_data.segment-1) * seg_length >= tlim[0] * fps)]
    else:
        raise ValueError('tlim must be None, int or list of 2 int')
    
    
    # determine the number of curves we want
    num_total = len(data.segment.drop_duplicates())
    if num_total < num_curves:
        seg_list = data.segment.drop_duplicates()
    else:
        seg_list = np.floor(num_total / num_curves * (np.arange(num_curves))) +  data.segment.min()
    
    fig = plt.figure()
    ax = fig.add_axes([0,0,1,1])
    for num, i in enumerate(seg_list):
        subdata = data.loc[data.segment==i]
        x, y = postprocess_gnf(subdata, lb, xlim=xlim, sparse=3)
        ax.plot(x, y, mec=bestcolor(num), label='{:d} s'.format(int(seg_length*(i-1)/fps)),
               ls='', marker=symbol_list[num], markersize=4, mfc=(0,0,0,0), mew=1)
        plot_data['l'+str(num)] = (x, y)
        
    ax.set_ylim([0.9, 11])
    ax.legend(ncol=2, loc='upper left')
    ax.loglog()
    ax.set_xlabel('$l^2/l_b^2$')
    ax.set_ylabel('$\Delta N/\sqrt{N}$')
    
    return plot_data, fig, ax

def plot_kinetics(k_data, i_data, tlim=None, xlim=None, lb=10, mpp=0.33, seg_length=100, fps=10):
    """
    Plot evolution of number fluctuation exponents and light intensity on a same yyplot
    refer to https://matplotlib.org/gallery/api/two_scales.html
    
    Args:
    k_data -- kinetics data computed by df2_kinetics.py
    i_data -- light intensity evolution extracted by overall_intensity.py
    lb -- size of bacteria (pixel, normalizing factor of x axis)
    mpp -- microns per pixel
    seg_length -- segment length when computing kinetics [frame]
    fps -- frames per second
    
    Returns:
    fig -- figure object
    ax1 -- the axis of kinetics
    """
    
    t = [] 
    power = []
    
    # apply tlim
    if tlim == None:
        pass
    elif isinstance(tlim, int):
        tc = (k_data.segment-1)*seg_length/fps
        k_data = k_data.loc[ tc < tlim]
        i_data = i_data.loc[i_data.t / fps < tlim]
    elif isinstance(tlim, list) and len(tlim) == 2:
        assert(tlim[1]>tlim[0])
        tc = (k_data.segment-1)*seg_length/fps
        k_data = k_data.loc[ (tc < tlim[1]) & (tc >= tlim[0])]
        i_data = i_data.loc[(i_data.t / fps < tlim[1]) & (i_data.t / fps >= tlim[0])]
    else:
        raise ValueError('tlim should be None, int or list of 2 int')     
    
    # compute exponents at different time
    # t, power will be plotted on ax1
    for idx in k_data.segment.drop_duplicates():
        subdata = k_data.loc[k_data.segment==idx]
        xx, yy = postprocess_gnf(subdata, lb, xlim=xlim, sparse=3)
        x = np.log(xx)
        y = np.log(yy)
        p = np.polyfit(x, y, deg=1)
        t.append((idx-1)*seg_length/fps)
        power.append(p[0])

    # rescale light intensity to (0, 1)
    # t1, i will be plotted on ax2
    t1 = i_data.t / fps
    i = i_data.intensity - i_data.intensity.min()
    i = i / i.max()

    # set up fig and ax
    fig = plt.figure()
    ax1 = fig.add_axes([0,0,1,1])
    ax2 = ax1.twinx()

    # plot t, power
    color = wowcolor(0)
    ax1.set_xlabel('$t$ [s]')
    ax1.set_ylabel('$\\alpha$', color=color)
    ax1.plot(t, power, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    # plot t1, intensity
    color = wowcolor(4)
    ax2.set_ylabel('$I$', color=color)
    ax2.plot(t1, i, color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    
    data = {'t0': t, 'alpha': power, 't1': t1, 'i': i}
    
    return data, fig, ax1

def kinetics_from_light_on(data):
    """
    Args:
    data -- dict of ('t0', 'alpha', 't1', 'i'), return value of plot_kinetics()
    
    Returns:
    new_data -- dict of ('t0', 'alpha', 't1', 'i'), where 't0' and 't1' are translated according to the light on time, so that light is on at time 0.
    """
    
    # find light on time
    i = data['i']
    i_thres = (i.max() + i.min()) / 2
    light_on_ind = (i>i_thres).replace(False, np.nan).idxmax()
    light_on_time = data['t1'][light_on_ind]
    
    # construct new_data
    new_data = {}
    for kw in data:
        if kw == 't0':
            new_data[kw] = np.array(data[kw])[data['t0']>=light_on_time] - light_on_time
        elif kw == 'alpha':
            new_data[kw] = np.array(data[kw])[data['t0']>=light_on_time]
        elif kw == 't1':
            new_data[kw] = np.array(data[kw])[data['t1']>=light_on_time] - light_on_time
        else:
            new_data[kw] = np.array(data[kw])[data['t1']>=light_on_time]
    
    # plot new_data
    fig = plt.figure()
    ax1 = fig.add_axes([0, 0, 1, 1])
    
    ax1.set_xlabel('$t$ [s]')
    ax1.set_ylabel('$\\alpha$')
    ax1.plot(new_data['t0'], new_data['alpha'])
    
    return new_data, fig, ax1

def plot_kinetics_eo(k_data, i_data, eo_data, tlim=None, xlim=None, lb=10, mpp=0.33, seg_length=100, fps=10):
    """
    Plot evolution of number fluctuation exponents and light intensity on a same yyplot
    In addition, plot flow energy and flow order in the same figure as well
    
    Args:
    k_data -- kinetics data computed by df2_kinetics.py
    i_data -- light intensity evolution extracted by overall_intensity.py
    eo_data -- energy and order data (t, E, OP), t has unit second, computed by energy_order.py
    tlim -- time range in which data is plotted
    xlim -- range for fitting the gnf curve
    lb -- size of bacteria (pixel, normalizing factor of x axis)
    mpp -- microns per pixel
    seg_length -- segment length when computing kinetics [frame]
    fps -- frames per second
    
    Returns:
    fig -- figure object
    ax1 -- the axis of kinetics
    """
    
    t = [] 
    power = []
    
    # apply tlim
    if tlim == None:
        pass
    elif isinstance(tlim, int):
        tc = (k_data.segment-1)*seg_length/fps
        k_data = k_data.loc[ tc < tlim]
        i_data = i_data.loc[i_data.t / fps < tlim]
        eo_data = eo_data.loc[eo_data.t < tlim]
    elif isinstance(tlim, list) and len(tlim) == 2:
        assert(tlim[1]>tlim[0])
        tc = (k_data.segment-1)*seg_length/fps
        k_data = k_data.loc[ (tc < tlim[1]) & (tc >= tlim[0])]
        i_data = i_data.loc[(i_data.t / fps < tlim[1]) & (i_data.t / fps >= tlim[0])]
        eo_data = eo_data.loc[(eo_data.t < tlim[1]) & (eo_data.t >= tlim[0])]
    else:
        raise ValueError('tlim should be None, int or list of 2 int')   
    
    # compute exponents at different time
    # t, power will be plotted on ax1
    for idx in k_data.segment.drop_duplicates():
        subdata = k_data.loc[k_data.segment==idx]
        xx, yy = postprocess_gnf(subdata, lb, xlim=xlim, sparse=3)
        x = np.log(xx)
        y = np.log(yy)
        p = np.polyfit(x, y, deg=1)
        t.append((idx-1)*seg_length/fps)
        power.append(p[0])

    # rescale light intensity to (0, 1)
    # t1, i will be plotted on ax2
    t1 = i_data.t / fps
    i = i_data.intensity - i_data.intensity.min()
    i = i / i.max()
    # t2, E will be plotted on ax3
    t2 = eo_data.t
    E = eo_data.E
    # t2, O will be plotted on ax4
    O = eo_data.OP
    
    # set up fig and ax
    fig = plt.figure()
    ax1 = fig.add_axes([0,0,1,1])
    ax2 = ax1.twinx()
    ax3 = ax1.twinx()
    ax4 = ax1.twinx()
    
    # plot t, power
    color = 'black'
    ax1.set_xlabel('$t$ [s]')
    ax1.set_ylabel('$\\alpha$', color=color)
    ax1.plot(t, power, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    # plot t1, intensity
    color = wowcolor(0)
    ax2.set_ylabel('$I$', color=color)
    ax2.plot(t1, i, color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    
    # plot t2, E
    color = wowcolor(2)
    ax3.set_ylabel('$E$', color=color)
    ax3.plot(t2, E, color=color)
    ax3.tick_params(axis='y', labelcolor=color)
    ax3.spines["right"].set_position(("axes", 1.1))
    
    # plot t2, O
    color = wowcolor(8)
    ax4.set_ylabel('$OP$', color=color)
    ax4.plot(t2, O, color=color)
    ax4.tick_params(axis='y', labelcolor=color)
    ax4.spines["right"].set_position(("axes", 1.2))
    
    ax = [ax1, ax2, ax3, ax4]
    
    data = {'t0': t, 'alpha': power, 't1': t1, 'i': i, 't2': t2, 'E': E, 'OP': O}
    
    return data, fig, ax

def kinetics_eo_from_light_on(data):
    """
    Args:
    data -- dict of (t0, alpha, t1, i, t2, E, OP), return value of plot_kinetics_eo()
    
    Returns:
    new_data -- dict of (t0, alpha, t1, i, t2, E, OP), modified so that light-on time is 0
    """
    
    # find light on time
    i = data['i']
    i_thres = (i.max() + i.min()) / 2
    light_on_ind = (i>i_thres).replace(False, np.nan).idxmax()
    light_on_time = data['t1'][light_on_ind]
    
    # construct new_data
    new_data = {}
    for kw in data:
        if kw == 't0' or kw == 't1' or kw == 't2':
            new_data[kw] = np.array(data[kw])[data[kw]>=light_on_time] - light_on_time
        elif kw == 'alpha':
            new_data[kw] = np.array(data[kw])[data['t0']>=light_on_time]
        elif kw == 'i':
            new_data[kw] = np.array(data[kw])[data['t1']>=light_on_time]
        else:
            new_data[kw] = np.array(data[kw])[data['t2']>=light_on_time]
    
    # plot new_data
    fig = plt.figure()
    ax1 = fig.add_axes([0, 0, 1, 1])
    
    color = 'black'
    ax1.set_xlabel('$t$ [s]')
    ax1.set_ylabel('$\\alpha$', color=color)
    ax1.plot(new_data['t0'], new_data['alpha'], color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    
    color = wowcolor(2)
    ax2 = ax1.twinx()
    ax2.set_ylabel('$E$', color=color)
    ax2.plot(new_data['t2'], new_data['E'], color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    
    color = wowcolor(8)
    ax3 = ax1.twinx()
    ax3.set_ylabel('$OP$', color=color)
    ax3.plot(new_data['t2'], new_data['OP'], color=color)
    ax3.tick_params(axis='y', labelcolor=color)
    ax3.spines["right"].set_position(("axes", 1.1))
    
    ax = [ax1, ax2, ax3]
    
    return new_data, fig, ax    

def kinetics_eo_smooth(data):
    """
    Generate smoothed data and plot them.
    
    Args:
    data -- dict of (t0, alpha, t1, i, t2, E, OP), return value of kinetics_eo_from_light_on(data) or plot_kinetics()
    
    Returns:
    new_data -- smoothed data, dict of (t0, alpha, t1, i, t2, E, OP)
    
    Note:
    Although there are many ways to smooth the curve, I apply here a gaussian filter with sigma=1/15*total_data_length to do the work.
    Also try uniform filter with same 'size'   
    """
    new_data = {}
    # Generate new_data
    for kw in data:
        if kw.startswith('t') == False:
            sigma = int(len(data[kw]) / 15) + 1
            new_data[kw] = gaussian_filter1d(data[kw], sigma)
#             new_data[kw] = uniform_filter1d(data[kw], sigma) 
        else:
            new_data[kw] = data[kw]
            
    # plot new_data
    fig = plt.figure()
    ax1 = fig.add_axes([0.2, 0.25, 0.5, 0.7])
    
    color = 'black'
    ax1.set_xlabel('$t$ [s]')
    ax1.set_ylabel('$\\alpha$', color=color)
    ax1.plot(new_data['t0'], new_data['alpha'], color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    
    color = wowcolor(2)
    ax2 = ax1.twinx()
    ax2.set_ylabel('$E$', color=color)
    ax2.plot(new_data['t2'], new_data['E'], color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    
    color = wowcolor(8)
    ax3 = ax1.twinx()
    ax3.set_ylabel('$OP$', color=color)
    ax3.plot(new_data['t2'], new_data['OP'], color=color)
    ax3.tick_params(axis='y', labelcolor=color)
    ax3.spines["right"].set_position(("axes", 1.2))
    
    ax = [ax1, ax2, ax3]
    
    return new_data, fig, ax

def df2(folder):
    l = readseq(folder)
    img = io.imread(l.Dir.loc[0])
    size_min = 5
    step = 50*size_min
    L = min(img.shape)
    boxsize = np.unique(np.floor(np.logspace(np.log10(size_min),
                        np.log10((L-size_min)/2),100)))
    
    df = pd.DataFrame()
    for num, i in l.iterrows():
        img = io.imread(i.Dir)
        framedf = pd.DataFrame()
        for bs in boxsize: 
            X, Y, I = divide_windows(img, windowsize=[bs, bs], step=step)
            tempdf = pd.DataFrame().assign(I=I.flatten(), t=int(i.Name), size=bs, 
                           number=range(0, len(I.flatten())))
            framedf = framedf.append(tempdf)
        df = df.append(framedf)

    df_out = pd.DataFrame()
    for number in df.number.drop_duplicates():
        subdata1 = df.loc[df.number==number]
        for s in subdata1['size'].drop_duplicates():
            subdata = subdata1.loc[subdata1['size']==s]
            d = s**2 * np.array(subdata.I).std()
            n = s**2 
            tempdf = pd.DataFrame().assign(n=[n], d=d, size=s, number=number)
            df_out = df_out.append(tempdf)

    average = pd.DataFrame()
    for s in df_out['size'].drop_duplicates():
        subdata = df_out.loc[df_out['size']==s]
        avg = subdata.drop(columns=['size', 'number']).mean().to_frame().T
        average = average.append(avg)
        
    return average


# fig3_spatial-correlations
def exp(x, a):
    return np.exp(-a*x)

def corr_length(data, fitting_range=None):
    """
    Args:
    data -- dataframe with columns (R, C), where R has pixel as unit
    fitting_range -- (optional) can be None, int or list of two int
    
    Returns:
    cl -- correlation length of given data (pixel)
    """
    if fitting_range == None:
        pass
    elif isinstance(fitting_range, int):
        data = data.loc[data['R'] < fitting_range]
    elif isinstance(fitting_range, list) and len(fitting_range) == 2:
        data = data.loc[(data['R'] < fitting_range[1])&(data['R'] >= fitting_range[0])]
    else:
        raise ValueError('fitting_range should be None, int or list of 2 int')
        
    fit = curve_fit(exp, data['R'], data['C'], p0=[0.01])
    cl = 1 / fit[0][0]
    return cl, fit

def xy_to_r(corr_xy):
    """
    Note, this version of function converts the xy data where x, y start from (step, step) instead of (0, 0).
    When the corr functions are changed, this function should not be used anymore. 
    Check carefully before using.
    
    Args:
    corr_xy -- DataFrame of (X, Y, ...)
    
    Returns:
    corr_r -- DataFrame (R, ...)
    """
    step_x = corr_xy.X.iloc[0]
    step_y = corr_xy.Y.iloc[0]
    corr_r = corr_xy.assign(R = ((corr_xy.X-step_x)**2 + (corr_xy.Y-step_y)**2)**0.5)    
    return corr_r

def average_data(directory, columns=['CA', 'CV']):
    """
    Take the average of all data in given directory
    
    Args:
    directory -- folder which contains *.csv data, with columns
    columns -- (optional) list of column labels of columns to be averaged
    
    Returns:
    averaged -- DataFrame with averaged data
    """
    k = 0
    
    l = corrLib.readdata(directory)
    for num, i in l.iterrows():
        data = pd.read_csv(i.Dir)
        # check if given label exists in data
        for label in columns:
            if label not in data:
                raise IndexError('Column \'{0}\' does not exist in given data'.format(label))
        if k == 0:
            temp = data[columns]
        else:
            temp += data[columns]
        k += 1                   
       
    # finally, append all other columns (in data but not columns) to averaged
    other_cols = []
    for label in data.columns:
        if label not in columns:
            other_cols.append(label) 
    
    averaged = pd.concat([temp / k, data[other_cols]], axis=1)       
    
    return averaged

def plot_correlation(data, plot_cols=['R', 'C'], xlim=None, mpp=0.33, lb=3, plot_raw=False):
    """
    Plot correlation data. Here we plot the exponential function fitting instead of raw data so that the curve look better.
    
    Args:
    data -- DataFrame (R, C, conc)
    plot_cols -- specify columns to plot. The first column should be distance and the second is correlation
    xlim -- trim the xdata, only use those in the range of xlim
    mpp -- microns per pixel 
    lb -- bacteria size in um
    
    Returns:
    ax -- the axis of plot, one can use this handle to add labels, title and other stuff   
    """
    
    # Initialization
    fig = plt.figure()
    ax = fig.add_axes([0,0,1,1])
    cl_data = {'conc': [], 'cl': []}
    symbol_list = ['o', '^', 'x', 's', '+']
    data = data.sort_values(by=[plot_cols[0], 'conc'])
    
    # process data, apply xlim
    if xlim == None:
        pass
    elif isinstance(xlim, int):
        data = data.loc[data[plot_cols[0]] < xlim]
    elif isinstance(xlim, list) and len(xlim) == 2:
        data = data.loc[(data[plot_cols[0]] < xlim[1])&(data[plot_cols[0]] >= xlim[0])]
    else:
        raise ValueError('xlim must be None, int or list of 2 ints')
    
    for num, nt in enumerate(data.conc.drop_duplicates()):
        subdata = data.loc[data.conc==nt]
        x = subdata[plot_cols[0]]
        y = subdata[plot_cols[1]]
        p, po = curve_fit(exp, x, y, p0=[0.01])
        xfit = np.linspace(0, x.max(), num=50)
        yfit = exp(xfit, *p)
        if plot_raw:
            ax.plot(x*mpp/lb, y, color=wowcolor(num), lw=1, ls='--')
        ax.plot(xfit*mpp/lb, yfit, mec=wowcolor(num), label=str(nt), ls='',
                marker=symbol_list[num], mfc=(0,0,0,0), markersize=4, markeredgewidth=0.5)
        cl_data['conc'].append(int(nt))
        cl_data['cl'].append(1/p[0])
    
    ax.legend()     
    return ax, pd.DataFrame(cl_data).sort_values(by='conc')


# fig-5 velocity and concentration
def retrieve_dxd_data(folder, log_list):
    """
    Args:
    folder -- folder containing dxd data
    log_list -- experiment log as a list object, format is ['date-num', ...]
    
    Returns:
    avg -- DataFrame with columns avg of given entry, adv_divv ... will be indices instead
    std -- DataFrame with columns std of given entry, adv_divv ... will be indices instead
    """
    for n, entry in enumerate(log_list):
        date, num = entry.split('-')
        temp = pd.read_csv(os.path.join(folder, date, 'div_x_dcadv', 'summary.csv'), index_col='sample').loc[[int(num)]]
        if n == 0:
            data = temp
        else:
            data = data.append(temp)
    data = data.transpose()
    avg = pd.DataFrame({'avg': data.mean(axis=1)})
    std = pd.DataFrame({'std': data.std(axis=1)})
    return avg, std