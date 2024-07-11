import numpy as np
import matplotlib.pyplot as plt

import torch as t
import torch.nn.functional as F

import os
import sys
sys.path.append('utils')

from utils.diffeo_container import diffeo_container


device = t.device("cuda") if t.cuda.is_available() else t.device("cpu")
print(f'Using {device} for inference')

# layer_num_list = list(range(6,44)) + [46]
layer_num_list = range(10,44)
read_path = '/vast/xj2173/diffeo/data/all_cnn_layers/'
# save_path = '/vast/xj2173/diffeo/process_data/all_cnn_layers/cosine_similarity/'
save_path = '/vast/xj2173/diffeo/process_data/all_cnn_layers/raw_cos_similarity/'
ref_path =  '/vast/xj2173/diffeo/data/reference/'

# inv_grid = t.load(read_path + '15-100-4-4-3-224-224_inv_grid_sample.pt', map_location= t.device('cpu'))
# inv_diffeos = diffeo_container(224, 224)
# inv_diffeos.diffeos = inv_grid

data_dir_list = []
ref_dir_list = []
for layer_num in layer_num_list:
    data_dir_list.append([s for s in os.listdir(read_path) if f'layer-{layer_num:02d}' in s and '15-100-4-4-3-224-224' in s])
    num_of_images = len(data_dir_list[-1])
    ref_dir_list.append([s for s in os.listdir(ref_path) if f'layer-{layer_num:02d}' in s][:num_of_images])


cosine_similarity_list = {}
for counter, (file_path_list, ref_path_list) in enumerate(zip(data_dir_list, ref_dir_list)):
    print(f'processing {layer_num_list[counter]}-th layer')
  
    activation = []
    ref_activation = []
    for file_path, ref_file_path in zip(file_path_list, ref_path_list):
        raw_data = t.load(read_path + file_path, map_location = t.device('cpu'))
        ref_data = t.load(ref_path + ref_file_path, map_location = t.device('cpu'))
        channels, x_res, y_res = raw_data.shape[-3:]
        # if f'{x_res},{y_res}' not in inv_diffeos.resampled.keys():
        #    down_sampled = inv_diffeos.up_down_sample(x_res, y_res, mode = 'nearest')
# 
        # un_diff = F.grid_sample(raw_data, t.cat(list(down_sampled)), mode = 'nearest', padding_mode='border')
        # activation.append(F.normalize(un_diff.reshape(15, 100, channels, x_res * y_res), dim = -1))
        activation.append(F.normalize(raw_data.reshape(15, 100, channels, x_res * y_res), dim = -1))
        ref_activation.append(F.normalize(ref_data.reshape(channels, x_res * y_res), dim = -1))
    
    activation = t.stack(activation) #img, strength, diffeo, channel, pixels
    ref_activation = t.stack(ref_activation)

    cosine_similarity = t.einsum('icp, isdcp -> isd', ref_activation, activation)/channels
    t.save(cosine_similarity, save_path + 'cosine_similarity' +f'_layer-{int(layer_num_list[counter]):02d}.pt')

    # cosine_similarity_list[f'{layer_num_list[counter]}'] = t.mean(cosine_similarity, dim = (0,2))



# diffeo_amp_list = [0.01, 0.05, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.275, 0.3, 0.35, 0.4, 0.45, 0.5]

# plt.figure()

# colors = plt.cm.viridis_r(np.linspace(0,1,len(cosine_similarity_list)))

# for i, key in enumerate(cosine_similarity_list.keys()):
#     layer_num = int(layer_num_list[i])
#     plt.plot(diffeo_amp_list, cosine_similarity_list[key], color=colors[i], label = f'layer {layer_num}')
#     plt.legend()
#     plt.xlabel(r'diffeo strength w/ L1 norm $|A|_1$')
#     plt.title('activation cosine similarity after naive inverse compared to no diffeo')
#     plt.ylabel(r'normalized averaged cosine similarity')

# plt.savefig(f'/vast/xj2173/diffeo/process_data/all_cnn_layers/cosine_similarity/all_layers.png')
# plt.close()