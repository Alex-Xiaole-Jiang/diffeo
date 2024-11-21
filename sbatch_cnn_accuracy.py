#%%
import torch as t
import torch.nn.functional as F
import torchvision as tv
from torchvision.transforms import v2

from utils.diffeo_container import sparse_diffeo_container, diffeo_container
from utils.get_model_activation import get_flatten_children

from tqdm import tqdm

device = t.device("cuda") if t.cuda.is_available() else t.device("cpu")
print(device)

torch_seed = 37
t.manual_seed(torch_seed)

# setting up path and config

ImageNet_path = '/vast/xj2173/diffeo/imagenet'
save_path = '/vast/xj2173/diffeo/scratch_data/steering/ENV2_s_NN/'
ref_path = '/vast/xj2173/diffeo/scratch_data/steering/ENV2_s_NN/reference/'

num_of_images = 100

diffeo_strengths = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
diffeo_strengths = [0.001, 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
# diffeo_strengths = [0.001]
num_of_diffeo = 20

inv_diffeo_save_path = ('/vast/xj2173/diffeo/scratch_data/inv_grids/'
                        f'{len(diffeo_strengths)}-{num_of_diffeo}-4-4-3-224-224_inv_grid_sample.pt')

steering_layers = list(range(3,44))
# steering_layers = [8, 20, 43]

# setting up helper function

def get_model():
  model = tv.models.efficientnet_v2_s(weights = tv.models.EfficientNet_V2_S_Weights.DEFAULT).to(device)
  # ENV2 = tv.models.efficientnet_v2_s().to(device) # random initialization
  model.eval();
  for param in model.parameters():
      param.requires_grad = False
  return model

def get_inference_transform():
  inference_transform = tv.models.EfficientNet_V2_S_Weights.IMAGENET1K_V1.transforms()
  inference_transforms = v2.Compose([
      lambda x: x.convert('RGB'),
      inference_transform,
  ])
  return inference_transforms

def get_ImageNet(transforms = None, batch_size = 1, shuffle = False):
  dataset = tv.datasets.ImageNet(ImageNet_path, split = 'val', transform = transforms)
  dataloader = t.utils.data.DataLoader(dataset, batch_size = batch_size, shuffle = shuffle)
  return dataset, dataloader

def get_diffeo_container(diffeo_strength_list = None, num_of_didffeo = None):
  diffeo_container = sparse_diffeo_container(224, 224)
  for strength in diffeo_strength_list:
      diffeo_container.sparse_AB_append(4, 4, 3, strength, num_of_didffeo)
  diffeo_container.get_all_grid()
  diffeo_container.to(device)
  return diffeo_container

def get_inverse_diffeo(diffeo_container, base_learning_rate = 500, epochs = 10000):
  inv_diffeo = diffeo_container.get_inverse_grid(base_learning_rate=base_learning_rate, epochs = epochs)
  return inv_diffeo

#%%
#
# where the code starts
model = get_model().to(device)

inf_transf = get_inference_transform()
dataset, dataloader = get_ImageNet(transforms = inf_transf, batch_size = 1, shuffle = True)
data_iter = iter(dataloader)

print('model & dataset setup finished', flush = True)
#%%
diffeos = get_diffeo_container(diffeo_strength_list = diffeo_strengths, num_of_didffeo = num_of_diffeo)
try:
  inv_diffeo = t.load(inv_diffeo_save_path, map_location = device)
except:
  inv_diffeo = get_inverse_diffeo(diffeos, base_learning_rate = 500, epochs = 200000)
  t.save(inv_diffeo, inv_diffeo_save_path)

print('diffeo & inverse computed', flush = True)
#%%
val_images = t.cat([next(data_iter)[0] for i in range(num_of_images)], dim = 0).to(device)
ref_output = model(val_images)
t.save(ref_output, ref_path + f'val_image-first-{num_of_images}-images-output.pt')

print('reference output computed & saved', flush = True)
#%%
model_layer = get_flatten_children(model)
steering_model_layers = [model_layer[index] for index in steering_layers]
steering_layer_shapes = get_steering_layer_shapes(model, steering_model_layers)
steering_inv_diffeo = get_steering_inv(inv_diffeo, steering_layer_shapes)
for diffeo in steering_inv_diffeo: diffeo.to(device)
hooks = steering_hooks(steering_model_layers, steering_inv_diffeo)

print('diffeo inv down sampled', flush = True)
# layers = list(range(3,44)) + [46] + [49]
#%%
for i, image in enumerate(tqdm(val_images)):
  file_prefix = f'{len(diffeo_strengths)}-{num_of_diffeo}-4-4-3-224-224_image-{i:04d}_steered'
  layers_in_string = '-'.join(str(num) for num in steering_layers)

  
  # get a list of shape [strength * diffeo (batch), channel, x, y]
  distorted_list = diffeos(image.repeat(num_of_diffeo * len(diffeo_strengths), 1,1,1), in_inference = True)
    
  with t.no_grad(): steered = model(distorted_list)
  # steered has shape [layer, strength, diffeo, -1]
  steered = t.reshape(steered, (len(steering_layers)+1, len(diffeo_strengths), num_of_diffeo, -1))
  t.save(steered, save_path + file_prefix + '_layer-' + layers_in_string +'.pt')
  
  # print(f'{i+1}th image completed', flush = True)

for hook in hooks: hook.remove()



# %%
print('yes')
# %%
