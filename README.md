# GossipSwap
<div align=“center”>
    <img src=“”, width=“900”>
</div>
----------------------------------------------------------------------------------------------------

# Contents
1. [Introduction](#Introduction)
2. [Install](#Install)
3. [Experiment](#Experiment)
4. [Citation](#Citation)
5. [Edit](#Edit)
## Introduction
Gossip Swap SGD is decentralized distributed machine learning method based on the Gossip SGD. This research was published at [APRIS2021](http://sigemb.jp/APRIS/2021/) and paper can be downloaded at [IPSJ](https://ipsj.ixsq.nii.ac.jp/ej/?action=pages_view_main&active_action=repository_view_main_item_detail&item_id=216195&item_no=1&page_id=13&block_id=8).
## Install
This source code is extended code of [PDMM SGD](https://github.com/nttcslab/edge-consensus-learning).When you use this code, please install the [PDMM SGD](https://github.com/nttcslab/edge-consensus-learning) and replace the some original files with this page's files.

You can see 3 directories in this repository. 
"exlsamples" is the directory which has two modified code of original one. If you want to use our Gossip Swap SGD, you must replace the original code to the our code. Please note that do not replace directory it own, replace same name files in the directory.
Ex) eclsamples/run_cifar10.py (original)->eclsamples/run_cifar10.py (ours)

"extended_conf" is the directory which has 4 new topology files and 2 new device files. When you want to use our experiment setting, down load all of files in this directory and install then in the original's "conf.json".

"extended_edgecons" is the directory which has 3 .py files. Each file has the changes for the Gossip Swap SGD. So when you run the Gossip Swap, you must replace original's code to the ours. Note that 3 .py files must be replaced to run the code. Do not install directory its own. Replace samename files in the edgecons.py.

Ex)edgecons/contract.py(origin)->edgecons/contract.py(ours)

## Experiment
Follow the [PDMM SGD](https://github.com/nttcslab/edge-consensus-learning).When you use this code, please install the [PDMM SGD](https://github.com/nttcslab/edge-consensus-learning)

If you want to run the Gossip Swap SGD, please overwrite the run_XXXX.py like a attached pdf file. And use gossip SGD command in the commnad line or terminal.
## Citation
```
@inproceedings{weko_216195_1,
   author	 = "Naoya,Yokota and Yuko,Hara-Azumi",
   title	 = "Weight Exchange in Decentralized Distributed Machine Learning for Resource-Constrained IoT Edges",
   booktitle	 = "Proceedings of Asia Pacific Conference on Robot IoT System Development and Platform",
   year 	 = "2022",
   volume	 = "2021",
   number	 = "",
   pages	 = "94--95",
   month	 = "jan"
}
```

##Edit
When you want know the way of editing, you can get it from pdf file. 
