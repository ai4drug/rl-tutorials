## 0、写在前面

本项目用于学习RL基础算法，尽量做到: **注释详细**(经过很长时间的纠结，还是中文注释好了！！！)，**结构清晰**。

代码结构主要分为以下几个脚本：

* ```[algorithm_name].py```：即保存算法的脚本，例如```dqn.py```，每种算法都会有一定的基础模块，例如```Replay Buffer```、```MLP```(多层感知机)等等；
* ```task.py```: 即保存任务的脚本，基本包括基于```argparse```模块的参数，训练以及测试函数等等；
* ```utils.py```：该脚本用于保存诸如存储结果以及画图的软件，在实际项目或研究中，推荐大家使用```Tensorboard```来保存结果，然后使用诸如```matplotlib```以及```seabron```来进一步画图。

## 运行环境

python 3.7、pytorch 1.6.0-1.9.0、gym 0.21.0

或者在```README.md```目录下执行以下命令复现环境：
```bash
conda env create -f environment.yaml
```
## 使用说明

直接运行带有```train```的py文件或ipynb文件会进行训练默认的任务；  
也可以运行带有```task```的py文件训练不同的任务

                                   
## Refs

[RL-Adventure-2](https://github.com/higgsfield/RL-Adventure-2)

[RL-Adventure](https://github.com/higgsfield/RL-Adventure)

[Google 开源项目风格指南——中文版](https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/python_style_rules/#comments)