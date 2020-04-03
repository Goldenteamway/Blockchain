## 直接运行

根据Pipfile的内容提前安装好相关的库，或者通过pipenv进行配置。

可以通过以下三种方式直接运行，**端口号默认5000**

* `$ python blockchain.py` 
* `$ python blockchain.py -p 5001` 
* `$ python blockchain.py --port 5002` 

## Docker运行

1.构建docker容器(**需要在Dockerfile文件路径下**)

```
$ docker build -t blockchain .
```

2.运行

```
$ docker run --rm -p 80:5000 blockchain
```

3.添加多个节点:

```
$ docker run --rm -p 81:5000 blockchain
$ docker run --rm -p 82:5000 blockchain
$ docker run --rm -p 83:5000 blockchain
```