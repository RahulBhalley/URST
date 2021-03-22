from __future__ import division
import torch
import torchfile
from modelsNIPS import decoder1,decoder2,decoder3,decoder4,decoder5
from modelsNIPS import encoder1,encoder2,encoder3,encoder4,encoder5
import torch.nn as nn
import sys
sys.path.append("../")
from thumb_instance_norm import ThumbWhitenColorTransform


class WCT(nn.Module):
    def __init__(self,args):
        super(WCT, self).__init__()
        # load pre-trained network
        vgg1 = torchfile.load(args.vgg1)
        decoder1_torch = torchfile.load(args.decoder1)
        vgg2 = torchfile.load(args.vgg2)
        decoder2_torch = torchfile.load(args.decoder2)
        vgg3 = torchfile.load(args.vgg3)
        decoder3_torch = torchfile.load(args.decoder3)
        vgg4 = torchfile.load(args.vgg4)
        decoder4_torch = torchfile.load(args.decoder4)
        vgg5 = torchfile.load(args.vgg5)
        decoder5_torch = torchfile.load(args.decoder5)

        
        self.e1 = encoder1(vgg1)
        self.d1 = decoder1(decoder1_torch)
        self.e2 = encoder2(vgg2)
        self.d2 = decoder2(decoder2_torch)
        self.e3 = encoder3(vgg3)
        self.d3 = decoder3(decoder3_torch)
        self.e4 = encoder4(vgg4)
        self.d4 = decoder4(decoder4_torch)
        self.e5 = encoder5(vgg5)
        self.d5 = decoder5(decoder5_torch)
        
        self.wct1 = ThumbWhitenColorTransform()
        self.wct2 = ThumbWhitenColorTransform()
        self.wct3 = ThumbWhitenColorTransform()
        self.wct4 = ThumbWhitenColorTransform()
        self.wct5 = ThumbWhitenColorTransform()
        
    
    def whiten_and_color(self, cF, sF):
        cFSize = cF.size()
        c_mean = torch.mean(cF,1) # c x (h x w)
        c_mean = c_mean.unsqueeze(1).expand_as(cF)
        cF = cF - c_mean
        contentConv = torch.mm(cF,cF.t()).div(cFSize[1]-1) + torch.eye(cFSize[0]).double()
        c_u,c_e,c_v = torch.svd(contentConv,some=False)

        k_c = cFSize[0]
        for i in range(cFSize[0]):
            if c_e[i] < 0.00001:
                k_c = i
                break

        sFSize = sF.size()
        s_mean = torch.mean(sF,1)
        sF = sF - s_mean.unsqueeze(1).expand_as(sF)
        styleConv = torch.mm(sF,sF.t()).div(sFSize[1]-1)
        s_u,s_e,s_v = torch.svd(styleConv,some=False)

        k_s = sFSize[0]
        for i in range(sFSize[0]):
            if s_e[i] < 0.00001:
                k_s = i
                break

        c_d = (c_e[0:k_c]).pow(-0.5)
        step1 = torch.mm(c_v[:,0:k_c],torch.diag(c_d))
        step2 = torch.mm(step1,(c_v[:,0:k_c].t()))
        whiten_cF = torch.mm(step2,cF)

        s_d = (s_e[0:k_s]).pow(0.5)
        targetFeature = torch.mm(torch.mm(torch.mm(s_v[:,0:k_s],torch.diag(s_d)),(s_v[:,0:k_s].t())),whiten_cF)
        targetFeature = targetFeature + s_mean.unsqueeze(1).expand_as(targetFeature)
        return targetFeature

    def transform_original(self, cF, sF, alpha):
        cF = cF.double()
        sF = sF.double()
        C, W, H = cF.size(0), cF.size(1), cF.size(2)
        _, W1, H1 = sF.size(0), sF.size(1), sF.size(2)
        cFView = cF.view(C, -1)
        sFView = sF.view(C, -1)
    
        targetFeature = self.whiten_and_color(cFView, sFView)
        targetFeature = targetFeature.view_as(cF)
        csF = alpha * targetFeature + (1.0 - alpha) * cF
        csF = csF.float().unsqueeze(0)
        return csF
    
    def transform(self, cF, sF, alpha=1.0, index=0, wct_mode='cpu'):
        cF = cF.double()
        sF = sF.double()
   
        C, W, H = cF.size(0), cF.size(1), cF.size(2)
        _, W1, H1 = sF.size(0), sF.size(1), sF.size(2)
        cFView = cF.view(C,-1)
        sFView = sF.view(C,-1)
        
        if index == 1:
            targetFeature = self.wct1(cFView, sFView, wct_mode)
        elif index == 2:
            targetFeature = self.wct2(cFView, sFView, wct_mode)
        elif index == 3:
            targetFeature = self.wct3(cFView, sFView, wct_mode)
        elif index == 4:
            targetFeature = self.wct4(cFView, sFView, wct_mode)
        elif index == 5:
            targetFeature = self.wct5(cFView, sFView, wct_mode)
            
        targetFeature = targetFeature.view_as(cF)
        csF = alpha * targetFeature + (1.0 - alpha) * cF
        csF = csF.float().unsqueeze(0)
        
        return csF
