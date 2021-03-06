# -*- coding: utf-8 -*-
import copy
import grpc
import io
import torch
import logging
from .pb.mnw_pb2 import Params as PbParams
from .pb.mnw_pb2 import SwapParams
from .pb.mnw_pb2_grpc import MnwServiceStub


class Edge:
    def __init__(self, edge_info, self_index, self_name, device, state_dict,
                 is_state=True, is_dual=True, is_avg=False, grpc_buf_size=524288, grpc_timeout=1.0, err_max_cnt=10):
        self._node_addr = edge_info["addr"]
        self._node_idx = edge_info["index"]
        self._self_idx = self_index
        self._self_name = self_name
        self._device = device
        self._grpc_err_cnt = 0
        self._grpc_buf_size = grpc_buf_size
        self._grpc_timeout = grpc_timeout
        self._err_max_cnt = err_max_cnt
        self.rcv_cnt=0
        self.compweight=0

        self._params_snd = {"state": None, "dual": None}
        self._params_rcv = {"state": None, "dual": None}
        self._dual_avg = None
        if is_state:
            self._params_snd["state"] = []
            self._params_rcv["state"] = []
        if is_dual:
            self._params_snd["dual"] = []
            self._params_rcv["dual"] = []
            if is_avg:
                self._dual_avg = []
        self._diff_buf = []

        for param_tensor in state_dict:
            if is_state:
                self._params_snd["state"].append(copy.deepcopy(state_dict[param_tensor]))
                self._params_rcv["state"].append(copy.deepcopy(state_dict[param_tensor]))
            if is_dual:
                self._params_snd["dual"].append(torch.zeros(state_dict[param_tensor].size(), device=device))
                self._params_rcv["dual"].append(torch.zeros(state_dict[param_tensor].size(), device=device))
                if is_avg:
                    self._dual_avg.append(copy.deepcopy(state_dict[param_tensor]))
            self._diff_buf.append(copy.deepcopy(state_dict[param_tensor]))

        self._prm_a = 1
        if self_index > self._node_idx:
            self._prm_a = -1
        '''print("self._node_addr")
        print(self._node_addr)'''
        self._swap_channel = grpc.insecure_channel(self._node_addr)

    def swap(self):
        is_connected = True
        try:
            swap_req_iter = self.SwapReqIter(self._self_name, self._params_snd, self._grpc_buf_size)
            params_buf = io.BytesIO()
            stub = MnwServiceStub(self._swap_channel)
            for res in stub.Swap(swap_req_iter, timeout=self._grpc_timeout):
                params_buf.write(res.params)
            params_buf.seek(0)
            self._params_rcv = torch.load(params_buf, map_location=torch.device(self._device))
            self._grpc_err_cnt = 0

        except grpc.RpcError:
            self._grpc_err_cnt += 1
            logging.warning("grpc timeout (%d/%d)" % (self._grpc_err_cnt, self._err_max_cnt))
            if self._err_max_cnt <= self._grpc_err_cnt:
                is_connected = False

        except RuntimeError:
            logging.warning("received data can't load")

        return is_connected

    class SwapReqIter(object):
        def __init__(self, self_name, params, grpc_buf_size):
            self._self_name = self_name
            self._grpc_buf_size = grpc_buf_size
            self._params_buf = io.BytesIO()
            torch.save(params, self._params_buf)
            self._params_buf.seek(0)

        def __iter__(self):
            return self

        def __next__(self):
            read_buf = self._params_buf.read(self._grpc_buf_size)
            if not read_buf:
                raise StopIteration()
            return SwapParams(src=self._self_name, params=read_buf)

    
    def update(self, p_data, index):
        if self._params_snd["state"] is not None:
            self._params_snd["state"][index] = p_data.clone()
        if self._params_snd["dual"] is not None:
            self._params_snd["dual"][index] = self._params_rcv["dual"][index] - 2 * self.prm_a() * p_data

    def get_send_params(self):
        send_buf = io.BytesIO()
        torch.save(self._params_snd, send_buf)
        return send_buf

    def set_recv_params(self, params):
        try:
            self._params_rcv = torch.load(io.BytesIO(params.getvalue()), map_location=torch.device(self._device))
            self.rcv_cnt=1
        except RuntimeError:
            logging.warning("received data can't load (srv)")

    def diff_buff(self):
        ret = None
        req = PbParams(src=self._self_name)
        try:
            params_buf = io.BytesIO()
            stub = MnwServiceStub(self._swap_channel)
            for res in stub.GetState(req, timeout=self._grpc_timeout):
                params_buf.write(res.params)
            params_buf.seek(0)
            ret = torch.load(io.BytesIO(params_buf.getvalue()), map_location=torch.device(self._device))
            self._grpc_err_cnt = 0

        except grpc.RpcError:
            logging.warning("grpc timeout (diff) (%d/%d)" % (self._grpc_err_cnt, self._err_max_cnt))
            self._grpc_err_cnt += 1

        except RuntimeError:
            logging.warning("received data can't load (diff)")

        return ret

    def rcv_state(self):
        return self._params_rcv["state"]

    def rcv_dual(self):
        return self._params_rcv["dual"]

    def dual_avg(self, index):
        self._dual_avg[index] = torch.div((self._dual_avg[index] + self._params_rcv["dual"][index]), 2)
        return self._dual_avg[index]

    def prm_a(self):
        return self._prm_a
