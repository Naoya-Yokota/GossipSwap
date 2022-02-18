# -*- coding: utf-8 -*-
import random
import grpc
import io
import time
import torch
import logging
from collections import OrderedDict
from concurrent import futures
from .edge import Edge
from .pb.mnw_pb2 import Status as PbStatus
from .pb.mnw_pb2 import Params as PbParams
from .pb.mnw_pb2 import StateParams, SwapParams
from .pb.mnw_pb2_grpc import MnwServiceStub
from .pb.mnw_pb2_grpc import MnwServiceServicer, add_MnwServiceServicer_to_server


class MnwGateway(MnwServiceServicer):
    def __init__(self, name, self_index, edges, edge_info, device, model,
                 is_state=True, is_dual=True, is_avg=False, grpc_buf_size=524288, grpc_timeout=1.0):
        self._name = name
        self._index = self_index
        self._edges = edges
        self._edge_info = edge_info
        self._device = device
        self._model = model
        self._is_state = is_state
        self._is_dual = is_dual
        self._is_avg = is_avg
        self._grpc_buf_size = grpc_buf_size
        self._grpc_timeout = grpc_timeout
        

    def Hello(self, request, context):
        if request.src not in self._edges:
            self._edges[request.src] = Edge(self._edge_info[request.src], self._index, self._name,
                                            self._device, self._model.state_dict(),
                                            self._is_state, self._is_dual, self._is_avg,
                                            self._grpc_buf_size, self._grpc_timeout)
        return PbStatus(status=200)

    def GetState(self, request, context):
        r_buf = io.BytesIO()
        torch.save(self._model.state_dict(), r_buf)
        r_buf.seek(0)
        while True:
            read_buf = r_buf.read(self._grpc_buf_size)
            if read_buf:
                yield StateParams(params=read_buf)
            else:
                break

    def Swap(self, request_iter, context):
        edge = None
        read_buf = io.BytesIO()

        for req in request_iter:
            if edge is None:

                '''communication test
                print("print req.src")
                print(req.src)'''

                edge = self._edges[req.src]
                send_buf = edge.get_send_params()
                send_buf.seek(0)
            bin_params = send_buf.read(self._grpc_buf_size)
            read_buf.write(req.params)
            yield SwapParams(src=self._name, params=bin_params)

        edge.set_recv_params(read_buf)


class Contract:
    def __init__(self, name, nodes, device, model, interval=10, offset=0,
                 is_state=True, is_dual=True, is_avg=False, grpc_buf_size=524288, grpc_timeout=1.0):
        self._update_interval = interval
        self._update_cnt = offset
        self._next_edge = 0
        self._edges = OrderedDict()
        self._server = None
        self.count=0
        self.com_weight={}
        self.total_weight=0
        self.comtable=[]
        self.node_name_list = []
        self.next_index=0
        self.self_name=name
        self.compweight=3
       

        # edge add

        node_name_list=[]
        for node in nodes:
            node_name_list.append(node["name"])
        self_index = node_name_list.index(name)
        if self_index == 0:
            state_req = False
        else:
            state_req = True

        edge_info = {}
        for edge_name in nodes[self_index]["edges"]:
            keys = list(self._edges.keys())
            if edge_name not in keys:
                edge_index = node_name_list.index(edge_name)
                edge_addr = nodes[edge_index]["addr"] + ":" + nodes[edge_index]["port"]
                edge_info[edge_name] = {"index": edge_index, "addr": edge_addr}
        self.node_name_list=node_name_list

        '''--define communication importance----'''
        '''---self_index 0: CASPER 1:BALTHASAL 2:MELCHIOR 3:KOUMEI----'''
        
        for edge_name in nodes[self_index]["edges"]:
            check_index=node_name_list.index(edge_name)
            importance=1
            self.total_weight+=1
            self.comtable.append(check_index)
            for check_edge in nodes[check_index]["edges"]:
                if check_edge in nodes[self_index]["edges"]:
                    importance+=0
                if check_edge not in nodes[self_index]["edges"] and node_name_list.index(check_edge)!=self_index:
                    importance+=1
                    self.total_weight+=1
                    self.comtable.append(check_index)
                self.com_weight[check_index]=importance
        

        
        print("communication importance")
        print(self.com_weight)
        print(self.total_weight)
        print(self.comtable)
        '''print("edge_info_this device")
        print(edge_info)'''
        
        # gRPC Server start
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=len(node_name_list)*2))
        add_MnwServiceServicer_to_server(MnwGateway(name, self_index, self._edges, edge_info, device,
                                                    model, is_state, is_dual, is_avg, grpc_buf_size, grpc_timeout),
                                         self._server)
        port_str = '[::]:' + nodes[self_index]["port"]
        self._server.add_insecure_port(port_str)
        self._server.start()

        for edge_name in nodes[self_index]["edges"]:
            keys = list(self._edges.keys())
            if edge_name not in keys:
                con = self.hello(name, edge_info[edge_name]["addr"], model, state_req)
                if con:
                    self._edges[edge_name] = Edge(edge_info[edge_name], self_index, name, device,
                                                  model.state_dict(), is_state, is_dual, is_avg,
                                                  grpc_buf_size, grpc_timeout)
                    state_req = False

        for edge in self._edges:
            if edge=="KOUMEI":
                self._edges[edge].compweight=3
            else:
                self._edges[edge].compweight=3
        
        
        '''---next edge test---'''
        ''''  
        if name == "CASPER":
            self._next_edge=list(self._edges.keys()).index("MELCHIOR")
        if name == "BALTHASAR":
            self._next_edge=list(self._edges.keys()).index("KOUMEI")
        if name =="KOUMEI":
            self._next_edge=list(self._edges.keys()).index("BALTHASAR")
        if name =="MELCHIOR":
            self._next_edge=list(self._edges.keys()).index("CASPER")
        '''
         
    def __del__(self):
        self._server.stop(0)

    @staticmethod
    def hello(name, addr, model, state_req, timeout_sec=10):
        connected = False
        cnt = 0
        while cnt < timeout_sec:
            with grpc.insecure_channel(addr) as channel:
                try:
                    req = PbParams(src=name)
                    stub = MnwServiceStub(channel)
                    response = stub.Hello(req)

                    if response.status == 200:
                        connected = True
                        if state_req:
                            device = next(model.parameters()).device
                            params_buf = io.BytesIO()
                            responses = stub.GetState(req)
                            for res in responses:
                                params_buf.write(res.params)
                            params_buf.seek(0)
                            model.load_state_dict(torch.load(io.BytesIO(params_buf.getvalue())))
                            model = model.to(device)
                        break
                except grpc.RpcError:
                    time.sleep(1)
                    cnt += 1

        return connected

    def swap(self):
        if len(list(self._edges.values())) > 0:
            self._update_cnt += 1
            if self._update_cnt >= self._update_interval:
                self._update_cnt = 0
                pull_edge = list(self._edges.values())[self._next_edge]  ##0x7f9c2ecf1e50
                '''print(pull_edge)
                print(self._edges)'''

                is_connected = pull_edge.swap()
                
                self.count+=1
                if not is_connected:
                    remove_edge_name = list(self._edges.keys())[self._next_edge]
                    del_number=self.comtable.count(self.next_index)
                    self.comtable=[edgename for edgename in self.comtable if edgename!= self.next_index]
                    self.total_weight=self.total_weight-del_number
                    self._edges.pop(remove_edge_name)
                    logging.info("%s : edge removed.", remove_edge_name)
                    print(self.comtable)
                    return 1
                if len(list(self._edges.values())) > 0:

                    #-----self.next_edge test code communicate with constant

                    
                    #self._next_edge=1
                    
                    #----- self._next_edge origin code---- 
                    
                    self._next_edge += 1
                    if self._next_edge >= len(self._edges):
                       self._next_edge = 0

                   
                    
                    #-----self._next_edge with network awaked----

                    '''
                    self.next_index=self.comtable[random.randint(0,self.total_weight-1)]
                    #print(self.next_index)
                    #print(self.node_name_list)
                    next_edge=self.node_name_list[self.next_index]
                    self._next_edge=list(self._edges.keys()).index(next_edge)
                    self.compweight=3
                    if next_edge=="KOUMEI":
                        self.compweight=4
                    '''
                   
                    
        return 0                   
     
    
    def edges(self):
        return self._edges

