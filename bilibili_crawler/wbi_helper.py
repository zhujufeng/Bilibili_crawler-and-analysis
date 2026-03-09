# -*- coding: utf-8 -*-
"""
bilibili_crawler/wbi_helper.py - B站 WBI 签名算法工具
"""
import time
from hashlib import md5
from typing import Dict
from urllib.parse import urlencode

# 混合密钥映射表
mixin_key_enc_tab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def get_mixin_key(orig: str):
    """对 imgKey 和 subKey 进行字符顺序打乱编码"""
    return ''.join([orig[i] for i in mixin_key_enc_tab])[:32]


def enc_wbi(params: Dict, img_key: str, sub_key: str):
    """
    为请求参数进行 WBI 签名
    :param params: 原始请求参数字典
    :param img_key: 提取的 img_key
    :param sub_key: 提取的 sub_key
    :return: 签名后的参数字典
    """
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())

    # 添加时间戳
    params['wts'] = curr_time

    # 按照 key 重排参数
    params = dict(sorted(params.items()))

    # # 过滤不用签名的字符
    # query_parts = []
    # for k, v in params.items():
    #     if isinstance(v, str):
    #         # 过滤 value 中的 "!'()*" 字符
    #         v = ''.join(filter(lambda ch: ch not in "!'()*", v))
    #     if v is None:
    #         continue
    #     query_parts.append(f'{k}={v}')
    #
    # query = '&'.join(query_parts)
    #
    # # 计算 w_rid
    # wbi_sign = md5((query + mixin_key).encode(encoding='utf-8')).hexdigest()
    # params['w_rid'] = wbi_sign
    # return params

    clean_params = {
        k: ''.join(filter(lambda ch: ch not in "!'()*", str(v)))
        for k, v in params.items()
    }

    # 4. 生成 Query String (这一步必须用标准库，保证和后续请求一致)
    query = urlencode(clean_params)

    # 5. 计算签名
    wbi_sign = md5((query + mixin_key).encode(encoding='utf-8')).hexdigest()

    # 6. 将签名写入参数
    params['w_rid'] = wbi_sign
    return params