"""
LL1 语法分析相关接口蓝图
包含 LL1 文法分析和输入串分析功能
"""
from flask import Blueprint, request, jsonify
from utils.Class_LL1_GrammarAnalysis import LL1

ll1_bp = Blueprint('ll1', __name__, url_prefix='/api')


@ll1_bp.route('/LL1Analyse', methods=['POST'])
def LL1anlyse():
    """LL1 文法分析"""
    data = request.get_json()
    text_list = data.get('inpProductions')
    ll1 = LL1(text_list)
    ll1.init()

    # dist<str , set>类型，其中value为set类型，不好转换json，将其转为list类型
    formulas_dict = ll1.formulas_dict
    first = ll1.first
    follow = ll1.follow
    for key in formulas_dict:
        formulas_dict[key] = list(formulas_dict[key])
    for key in first:
        first[key] = list(first[key])
    for key in follow:
        follow[key] = list(follow[key])

    # dist<tuple , str>， 其中key为tuple类型，不好转换json，将其转为str类型
    table = ll1.table
    new_table = {}
    for (x, y), value in table.items():
        # 将元组键转换为字符串，这里使用 | 作为分隔符
        new_key = f"{x}|{y}"
        new_table[new_key] = value

    data = {
        "S": ll1.S,
        "Vn": ll1.Vn,
        "Vt": ll1.Vt,
        "formulas_dict": formulas_dict,
        "first": first,
        "follow": follow,
        "table": new_table,
        "isLL1": ll1.isLL1
    }

    return jsonify({
        "code": 0,
        "data": data
    }), 200


@ll1_bp.route('/LL1AnalyseInp', methods=['POST'])
def LL1AnlyseInp():
    """LL1 输入串分析"""
    data = request.get_json()
    text_list = data.get('inpProductions')
    inp_str = data.get('inpStr')
    ll1 = LL1(text_list)
    ll1.init()
    ll1.solve(inp_str)
    return jsonify({
        "code": 0,
        "data": ll1.info
    }), 200
