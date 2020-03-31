import requests
import hashlib
import json
from time import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4
from argparse import ArgumentParser
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        # 当前交易
        self.current_transactions = []
        # 链
        self.chain = []
        # 节点集合
        self.nodes = set()
        # 创建创世块
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address: str) -> None:
        """
        在节点集合中新增加一个节点

        :param address: 节点的地址. Eg. 'http://192.168.0.2:5000'
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain: List[Dict[str, Any]]) -> bool:
        """
        校验整条链是否合法

        :param chain: 一条链
        :return: 返回校验结果
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # 检查链的哈希值是否正确
            if block['previous_hash'] != self.hash(last_block):
                return False

            # 进行链的有效性验证
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self) -> bool:
        """
        共识算法解决冲突
        使用网络中最长的链.

        :return:  如果链被取代返回 True, 否则为False
        """

        neighbours = self.nodes
        new_chain = None

        # 寻找当前最长链
        max_length = len(self.chain)

        # 比较验证网络中所有节点的链条
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # 若发现新的最长链，则进行替换
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof: int, previous_hash: Optional[str]) -> Dict[str, Any]:
        """
        生成新块

        :param proof: 工作量证明，随机数Nonce
        :param previous_hash: 上一个块的哈希值
        :return: 返回一个新块
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # 将当前交易信息重置，为后续区块的交易信息做准备
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: int) -> int:
        """
        生成新交易信息，信息将加入到下一个待挖的区块中

        :param sender: 发送方的地址
        :param recipient: 接收方的地址
        :param amount: 交易金额
        :return: 返回上一个交易的索引+1，以便输出
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]

    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        """
        生成块的 SHA-256 hash值

        :param block: 区块
        """

        # 对于区块字典的信息进行排序，保证有序性，否则生成的Hash会不一致。
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof: int) -> int:
        """
        简单的工作量证明:
         - 查找一个 p' 使得 hash(pp') 以4个0开头
         - p 是上一个块的证明,  p' 是当前的证明
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int) -> bool:
        """
        验证证明: 是否hash(last_proof, proof)以4个0开头

        :param last_proof: 上一个区块的工作量证明
        :param proof: 当前工作量证明
        :return: 验证合法性
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


app = Flask(__name__)

# 为节点生成一个唯一的UUID地址
node_identifier = str(uuid4()).replace('-', '')

# 初始化区块链
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # 运行工作量证明算法，得到下一个工作量证明
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # 给工作量证明的节点提供奖励.
    # 发送者为 "0" 表明是新挖出的币
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    block = blockchain.new_block(proof, None)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # 检查POST数据
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # 创建一个新的交易
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':

    # 参数添加及解析
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)
