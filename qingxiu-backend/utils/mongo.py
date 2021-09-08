# -*- coding: utf-8 -*-
# @Time : 2020/09/014
# @Author : hongjian
import pymongo


class Mongo:
    """
    MongoDB 通用操作类
    """

    def __init__(self, collection=None):
        """
        初始化 Mongo 连接客户端
        确定 数据库 和 集合
        """
        self.client = pymongo.MongoClient(
            'mongodb://tuanzi:tuanzi@127.0.0.1:27017')
        self.db = self.client['tuanzi']
        self.col = self.db[collection] if collection else None

    def get_col(self):
        """
        :return: mongo 集合
        """
        return self.col

    def insert_one(self, data: dict):
        """
        :param data: 待插入文档 (dict)
        :return: 插入数据的 _id （ObjectId）
        """
        return self.col.insert_one(data).inserted_id

    def insert(self, data: list):
        """
        :param data: 待插入文档 ([dict])
        :return: 插入数据的 _id 列表 （[ObjectId]）
        """
        return self.col.insert_many(data)

    def select_one(self, condition=None):
        """
        :param condition: 查询条件 (dict)
        :return: 查询结果 （dict）
        """
        if condition is None:
            condition = {}
        return self.col.find_one(condition)

    def select_many(self, condition=None):
        """
        :param condition: 查询条件 (dict)
        :return: 查询结果 （pymongo.cursor.Cursor）
        """
        if condition is None:
            condition = {}
        return self.col.find(condition)


if __name__ == '__main__':
    result = Mongo('test').select_many()
    print(type(result), result)
