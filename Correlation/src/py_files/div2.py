import corrLib
import sys
import os
from skimage import io
import pdb
import matplotlib as mpl
import matplotlib.pyplot as plt
plt.switch_backend('agg')
import pandas as pd
import time

piv_folder = sys.argv[1]
imgDir = sys.argv[2]
output_folder = sys.argv[3]
winsize = int(sys.argv[4])
step = int(sys.argv[5])

# piv_folder = r'E:\Google Drive\data_share\Dynamics_raw\concentration_velocity_field\piv_result_50\80'
# imgDir = r'E:\Google Drive\data_share\Dynamics_raw\processed_image\80_bp\900.tif'
# output_folder = r'E:\Github\Python\Correlation\test_images\div\div2test'
# winsize = 50
# step = 25

if os.path.exists(output_folder) == 0:
    os.makedirs(output_folder)
with open(os.path.join(output_folder, 'log.txt'), 'w') as f:
    pass

count = 0
ld = corrLib.readdata(piv_folder)
img = io.imread(imgDir)
for num, i in ld.iterrows():
    pivData = pd.read_csv(os.path.join(piv_folder, i.Dir))
    folder, file = os.path.split(i.Dir)
    name_ind = file.find('-')
    name = file[0: name_ind]
    c, v, divcn, divcv, divv = corrLib.div_field(img, pivData, winsize, step)
    X, Y, I = corrLib.divide_windows(img, windowsize=[winsize, winsize], step=step)
    data = pd.DataFrame().assign(x=X.flatten(), y=Y.flatten(), div=divv.flatten())
    data.to_csv(os.path.join(output_folder, i.Name+'.csv'), index=False)
    with open(os.path.join(output_folder, 'log.txt'), 'a') as f:
        f.write(time.asctime() + ' // ' + name + ' calculated\n')

""" SYNTAX
python div2.py piv_folder imgDir output_folder winsize step
"""
        
""" TEST PARAMS
piv_folder = E:\Google Drive\data_share\Dynamics_raw\concentration_velocity_field\piv_result_50\80
imgDir = E:\Google Drive\data_share\Dynamics_raw\processed_image\80_bp\900.tif
output_folder = E:\Github\Python\Correlation\test_images\div\div2test
winsize = 50
step = 25
"""

""" LOG 3 sec / frame
Tue Apr 21 20:09:27 2020 // 900 calculated
"""