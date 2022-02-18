# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
from torch.optim.sgd import SGD
from .contract import Contract


class GossipSGD(SGD):
    def __init__(self, name, nodes, device, model, interval=10, offset=0,
                 lr=0.05, momentum=0, dampening=0, weight_decay=0, nesterov=False):
        super(GossipSGD, self).__init__(model.parameters(), lr, momentum, dampening, weight_decay, nesterov)
        self._contract = Contract(name, nodes, device, model, interval, offset, is_dual=False)
        self._diff = torch.tensor(0., device=device)
        self._criterion = nn.MSELoss()
        for group in self.param_groups:
            group["initial_lr"] = lr
        self.weight=3
        self.swapcnt=0
        if name=="KOUMEI":
            self.weight=4

        self.swap_param=self.param_groups
        self.hold=name
    def __setstate__(self, state):
        super(GossipSGD, self).__setstate__(state)
        for group in self.param_groups:
            group.setdefault('nesterov', False)

    @torch.no_grad()
    def update(self):
        #自分と繋がっているedgeが帰ってくる。

        edges = self._contract.edges()  ##([('BALTHASAR', <edgecons.edge.Edge object at 0x7f9c2ecf1e50>)

        '''元のコード '''
        for edge in edges.values(): #それぞれのedgeに対しての処理
            '''if edge.rcv_cnt==1:
                edge.rcv_cnt=0'''
            for group in self.param_groups:
                for i, p in enumerate(group['params']):
                    d_p = p.data
                    p.data = torch.div((d_p + edge.rcv_state()[i]), 2)
                    edge.update(p.data, i)

        finish=self._contract.swap()
        return finish

    
    @torch.no_grad()
    def skipswap(self):
        #自分と繋がっているedgeが帰ってくる。

        edges = self._contract.edges()  ##([('BALTHASAR', <edgecons.edge.Edge object at 0x7f9c2ecf1e50>)


        for edge in edges.values():
            if edge.rcv_cnt==1:
                edge.rcv_cnt=0
                if edge._self_name!=self.hold:
                    self.hold=edge._self_name
                    for group in self.swap_param:
                        for i, p in enumerate(group['params']):
                            d_p = p.data
                            p.data =  edge.rcv_state()[i]
                            edge.update(d_p, i)

                else:
                    for group in self.param_groups:
                         for i, p in enumerate(group['params']):
                            d_p = p.data
                            p.data =  edge.rcv_state()[i]
                            edge.update(d_p, i)
                    
    
        finish=self._contract.swap()
        return finish


    @torch.no_grad()
    def swapupdate(self):
        #自分と繋がっているedgeが帰ってくる。

        edges = self._contract.edges()  ##([('BALTHASAR', <edgecons.edge.Edge object at 0x7f9c2ecf1e50>)

        '''モデル交換のみを行う '''
        
        for edge in edges.values():
            if edge.rcv_cnt==1:
                edge.rcv_cnt=0
            for group in self.param_groups:
                for i, p in enumerate(group['params']):
                    d_p = p.data
                    p.data =  edge.rcv_state()[i]
                    edge.update(d_p, i)
                    
                    
    
        finish=self._contract.swap()
        return finish

    @torch.no_grad()
    def weightupdate(self):
        #自分と繋がっているedgeが帰ってくる。
        #重みの更新式が少し変

        edges = self._contract.edges()  ##([('BALTHASAR', <edgecons.edge.Edge object at 0x7f9c2ecf1e50>)

        '''データの加重平均更新'''
        div=self.weight
        for edge in edges.values():
            if edge.rcv_cnt==1:
                edge.rcv_cnt=0
                div=div+edge.compweight
            for group in self.param_groups:
                for i, p in enumerate(group['params']):
                    d_p = p.data*self.weight
                    p.data = torch.div((d_p*self.weight + edge.rcv_state()[i]*edge.compweight), div)
                    edge.update(p.data, i)

        finish=self._contract.swap()
        return finish
            
        

    @torch.no_grad()
    def diff(self):
        edges = self._contract.edges()
        torch.nn.init.zeros_(self._diff)

        for edge in edges.values():
            diff_buf = edge.diff_buff()
            buf_name_list = list(diff_buf)
            for group in self.param_groups:
                for i, p in enumerate(group['params']):
                    self._diff += self._criterion(p.data, diff_buf[buf_name_list[i]])

        return self._diff
    def printing(self):
        print(self._contract.count)
