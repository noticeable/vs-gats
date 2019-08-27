import torch.nn as nn
from collections import OrderedDict

class Identity(nn.Module):
    def __init__(self):
        super(Identity,self).__init__()

    def forward(self, x):
        return x

def get_activation(name):
    if name=='ReLU':
        return nn.ReLU(inplace=True)
    elif name=='Tanh':
        return nn.Tanh()
    elif name=='Identity':
        return Identity()
    elif name=='Sigmoid':
        return nn.Sigmoid()
    elif name=='LeakyReLU':
        return nn.LeakyReLU(0.2,inplace=True)
    else:
        assert(False), 'Not Implemented'

class MLP(nn.Module):
    def __init__(self, layer_sizes, activation, bias=True, use_bn=True, drop_prob=None):
        '''
        Args:
             layer_sizes: a list, the size of each layer you want to construct: [1024,1024,...]
              activation: a list, the activations of each layer you want to use: ['ReLU', 'Tanh',...]
                  use_bn: bool, use batch normalize or not
               drop_prob: default is None, use drop out layer or not
        '''
        super(MLP, self).__init__()
        self.layers = nn.ModuleList()
        for i in range(len(layer_sizes)-1):
            layer = nn.Linear(layer_sizes[i], layer_sizes[i+1], bias=bias)
            activate = get_activation(activation[i])
            block = nn.Sequential(
                OrderedDict([(f'L{i}', layer), 
                             (f'A{i}', activate)
                            ]))
            if use_bn:
                bn = nn.BatchNorm1d(layer_sizes[i+1])
                block.add_module(f'B{i}', bn)
            if drop_prob is not None:
                block.add_module(f'D{i}', nn.Dropout(drop_prob))
            self.layers.append(block)
    
    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

# construct the classifier
class Predictor(nn.Module):
    def __init__(self, in_feat, num_calss):
        super(Predictor, self).__init__()
        self.classifier = nn.Linear(in_feat, num_calss)
        self.sigmoid = nn.Sigmoid()

    def forward(self, h_f):
        output = self.classifier(h_f)
        # if the criterion is BCELoss, you need to uncomment the following code
        # output = self.sigmoid(output)
        return output
