from __future__ import print_function
import sys
import os
import ipdb
import pickle
import h5py
import argparse
import numpy as np
from tqdm import tqdm

import dgl
import networkx as nx
import torch
import torch.nn as nn
import torchvision
from torch.utils.data import DataLoader

from model.model import AGRNN
from datasets.hico_constants import HicoConstants
from datasets import metadata
import utils.io as io

def main(args, data_const):
    # use GPU if available else revert to CPU
    device = torch.device('cuda:0' if torch.cuda.is_available() and args.gpu else 'cpu')
    print("Testing on", device)

    # Load checkpoint and set up model
    try:
        # load checkpoint
        checkpoint = torch.load(args.pretrained, map_location=device)
        # in_feat, out_feat, hidden_size, action_num  = checkpoint['in_feat'], checkpoint['out_feat'],\
                                                        # checkpoint['hidden_size'], checkpoint['action_num']
        print('Checkpoint loaded!')
        # set up model and initialize it with uploaded checkpoint
        # model = GRNN(in_feat=in_feat, out_feat=out_feat, hidden_size=hidden_size, action_num=action_num)
        model = AGRNN()
        model.load_state_dict(checkpoint['state_dict'])
        model.to(device)
        model.eval()
        print('Constructed model successfully!')
    except Exception as e:
        print('Failed to load checkpoint or construct model!', e)
        sys.exit(1)
    
    print('Creating hdf5 file for predicted hoi dets ...')
    if not os.path.exists(data_const.result_dir):
        os.mkdir(data_const.result_dir)
    pred_hoi_dets_hdf5 = os.path.join(data_const.result_dir, 'pred_hoi_dets.hdf5')
    pred_hois = h5py.File(pred_hoi_dets_hdf5,'w')
    # print('Creating json file for predicted hoi dets ...')
    hoi_box_score = {}
    # prepare for data
    dataset_list = io.load_json_object(data_const.split_ids_json)
    test_list = dataset_list['test']
    test_data = h5py.File(data_const.hico_test_data, 'r')
    for global_id in tqdm(test_list): 
        if global_id not in test_data.keys(): continue
        train_data = test_data[global_id]
        img_name = global_id + '.jpg'
        det_boxes = train_data['boxes'][:]
        roi_labels = train_data['classes'][:]
        roi_scores = train_data['scores'][:]
        node_num = train_data['node_num'].value
        node_labels = train_data['node_labels'][:]
        features = train_data['feature'][:]
        if node_num == 0 or node_num == 1: continue
        # referencing
        features = torch.FloatTensor(features).to(device)
        outputs, atten = model(node_num, features, roi_labels)
        
        action_score = nn.Sigmoid()(outputs)
        action_score = action_score.cpu().detach().numpy()
        atten = atten.cpu().detach().numpy()
        # save detection result
        # hoi_box_score[file_name.split('.')[0]] = {}
        pred_hois.create_group(global_id)
        det_data_dict = {}
        h_idxs = np.where(roi_labels == 1)[0]
        for h_idx in h_idxs:
            for i_idx in range(len(roi_labels)):
                if i_idx == h_idx:
                    continue
                if h_idx > i_idx:
                    score = roi_scores[h_idx] * roi_scores[i_idx] * (action_score[h_idx] + action_score[i_idx]) * atten[h_idx][i_idx]
                else:
                    score = roi_scores[h_idx] * roi_scores[i_idx] * (action_score[h_idx] + action_score[i_idx]) * atten[h_idx][i_idx-1]
                try:
                    hoi_ids = metadata.obj_hoi_index[roi_labels[i_idx]]
                except Exception as e:
                    ipdb.set_trace()
                for hoi_idx in range(hoi_ids[0]-1, hoi_ids[1]):
                    hoi_pair_score = np.concatenate((det_boxes[h_idx], det_boxes[i_idx], np.expand_dims(score[metadata.hoi_to_action[hoi_idx]], 0)), axis=0)
                    if str(hoi_idx+1).zfill(3) not in det_data_dict.keys():
                        det_data_dict[str(hoi_idx+1).zfill(3)] = hoi_pair_score[None,:]
                    else:
                        det_data_dict[str(hoi_idx+1).zfill(3)] = np.vstack((det_data_dict[str(hoi_idx+1).zfill(3)], hoi_pair_score[None,:]))
        for k, v in det_data_dict.items():
            pred_hois[global_id].create_dataset(k, data=v)
    # io.dump_json_object(hoi_box_score, os.path.join(result_path, 'pred_hoi_dets.json'))
    # pickle.dump(hoi_box_score, open(os.path.join(result_path, 'pred_hoi_dets.p'), 'wb'))

    pred_hois.close()

def str2bool(arg):
    arg = arg.lower()
    if arg in ['yes', 'true', '1']:
        return True
    elif arg in ['no', 'false', '0']:
        return False
    else:
        # raise argparse.ArgumentTypeError('Boolean value expected!')
        pass

if __name__ == "__main__":
    # set some arguments
    parser = argparse.ArgumentParser(description='Evalute the model')

    parser.add_argument('--pretrained', '-p', type=str, default='checkpoints/v2/epoch_train/checkpoint_100_epoch.pth',
                        help='Location of the checkpoint file: ./checkpoints/checkpoint_150_epoch.pth')

    parser.add_argument('--gpu', type=str2bool, default='true',
                        help='use GPU or not: true')

    args = parser.parse_args()
    data_const = HicoConstants()
    # inferencing
    main(args, data_const)