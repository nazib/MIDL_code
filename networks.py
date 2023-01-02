from collections import OrderedDict

import torch
import torch.nn as nn
from BAM import BAM

class UNet(nn.Module):

    def __init__(self, in_channels=1, out_channels=5, init_features=64):
        super(UNet, self).__init__()

        features = init_features
        #self.encoder0 = UNet._block(in_channels, features, name="enc1",stride=1)
        self.encoder1 = UNet._block(in_channels, features*1, name="enc1",stride=1)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.encoder2 = UNet._block(features, features * 2, name="enc2",stride=1)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.encoder3 = UNet._block(features * 2, features * 4, name="enc3",stride=1)
        self.pool3 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.encoder4 = UNet._block(features * 4, features * 8, name="enc4",stride=1)
        self.pool4 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        self.bottleneck = UNet._block(features * 8, features * 16, name="bottleneck",stride=2)

        self.upconv4 = nn.ConvTranspose2d(
            features * 16, features * 8, kernel_size=2, stride=2
        )
        self.decoder4 = UNet._block((features * 8) * 2, features * 8, name="dec4")
        self.upconv3 = nn.ConvTranspose2d(
            features * 8, features * 4, kernel_size=2, stride=2
        )
        self.decoder3 = UNet._block((features * 4) * 2, features * 4, name="dec3")
        self.upconv2 = nn.ConvTranspose2d(
            features * 4, features * 2, kernel_size=2, stride=2
        )
        self.decoder2 = UNet._block((features * 2) * 2, features * 2, name="dec2")
        self.upconv1 = nn.ConvTranspose2d(
            features * 2, features, kernel_size=2, stride=2
        )
        self.decoder1 = UNet._block(features * 2, features, name="dec1")
        self.upconv0 = nn.ConvTranspose2d(
            features, features, kernel_size=2, stride=2
        )
        
        self.conv = nn.Conv2d(
            in_channels=features, out_channels=out_channels, kernel_size=1
        )

        #### Uncertainty modules ###
        self.attenion = U_Attention(features * 16) 
        

    def forward(self, x,weights=None):
        #enc0 = self.encoder0(x)
        enc1 = self.encoder1(self.pool1(x))
        enc2 = self.encoder2(self.pool2(enc1))
        enc3 = self.encoder3(self.pool3(enc2))
        enc4 = self.encoder4(self.pool4(enc3))
        
        bottleneck = self.bottleneck(enc4)
        if isinstance(weights,torch.Tensor):
            bottleneck = self.attenion(weights,bottleneck)
        
        dec4 = self.upconv4(bottleneck)
        dec4 = torch.cat((dec4, enc4), dim=1)
        dec4 = self.decoder4(dec4)
        dec3 = self.upconv3(dec4)
        dec3 = torch.cat((dec3, enc3), dim=1)
        dec3 = self.decoder3(dec3)
        dec2 = self.upconv2(dec3)
        dec2 = torch.cat((dec2, enc2), dim=1)
        dec2 = self.decoder2(dec2)
        dec1 = self.upconv1(dec2)
        dec1 = torch.cat((dec1, enc1), dim=1)
        dec1 = self.decoder1(dec1)
        dec1 = self.upconv0(dec1)

        output = self.conv(dec1)
        return output
    
    @staticmethod
    def _block(in_channels, features, name,stride=1):
        return nn.Sequential(
            OrderedDict(
                [
                    (
                        name + "conv1",
                        nn.Conv2d(
                            in_channels=in_channels,
                            out_channels=features,
                            kernel_size=3,
                            padding=1,
                            bias=False
                        ),
                    ),
                    (name + "norm1", nn.BatchNorm2d(num_features=features)),
                    (name + "relu1", nn.ReLU(inplace=True)),
                    (
                        name + "conv2",
                        nn.Conv2d(
                            in_channels=features,
                            out_channels=features,
                            kernel_size=3,
                            padding=1,
                            bias=False,
                            stride=stride
                        ),
                    ),
                    (name + "norm1", nn.BatchNorm2d(num_features=features)),
                    (name + "relu1", nn.ReLU(inplace=True)),
                ]
            )
        )

class U_Attention(nn.Module):
    def __init__(self,bottleneck_dim,reduction_ratio=16,dilation_num=2,dilation_val=4):
        super(U_Attention,self).__init__()
        self.attention = nn.Sequential()
        self.features = bottleneck_dim
        self.shape = (1,bottleneck_dim,256,256)
        self.attention.add_module("attSoftmax",nn.Softmax2d())
        self.attention.add_module("attDown",nn.Conv2d(self.features,self.features,kernel_size=2,stride=32))
        '''
        self.attention.add_module("attConv1",nn.Conv2d(in_channels=1,out_channels=self.features,kernel_size=1))
        self.attention.add_module( 'attBN',	nn.BatchNorm2d(self.features//reduction_ratio) )
        self.attention.add_module( 'attRL',nn.ReLU() )
        self.attention.add_module("attConv3_di",nn.Conv2d(in_channels=self.features,
        out_channels=self.features, kernel_size=3,dilation=dilation_val))
        '''
        self.attention.add_module("Spatial_BAM",BAM(self.features))
    
    def forward(self,weights,bottleneck):
        weight_list = []
        for i in range(self.features):
            weight_list.append(weights)
        weights = torch.stack(weight_list,dim=1)
        weights = torch.reshape(weights,self.shape)
        weights = weights.to("mps")
        attention = self.attention(weights)
        new_bottleneck = attention * bottleneck
        return new_bottleneck


