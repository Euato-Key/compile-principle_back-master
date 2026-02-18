"""
SLR1 语法分析相关接口蓝图
包含 SLR1 文法分析和输入串分析功能
"""
from flask import Blueprint, request, jsonify
from utils.Class_SLR1_GrammarAnalysis import SLR1

slr1_bp = Blueprint('slr1', __name__, url_prefix='/api')


@slr1_bp.route('/SLR1Analyse', methods=['POST'])
def SLR1Anlyse():
    """SLR1 文法分析"""
    data = request.get_json()
    text_list = data.get('inpProductions')
    slr1 = SLR1(text_list)
    slr1.init()

    # dist<tuple , str>， 其中key为tuple类型，不好转换json，将其转为str类型
    actions = slr1.actions
    gotos = slr1.gotos
    new_actions = {}
    new_gotos = {}
    for (x, y), value in actions.items():
        # 将元组键转换为字符串，这里使用 | 作为分隔符
        new_key = f"{x}|{y}"
        new_actions[new_key] = value
    for (x, y), value in gotos.items():
        # 将元组键转换为字符串，这里使用 | 作为分隔符
        new_key = f"{x}|{y}"
        new_gotos[new_key] = value

    # 处理First和Follow集合，将set类型转换为list类型以便JSON序列化
    first = slr1.first
    follow = slr1.follow
    for key in first:
        first[key] = list(first[key])
    for key in follow:
        follow[key] = list(follow[key])

    data = {
        "S": slr1.S,
        "Vn": slr1.Vn,
        "Vt": slr1.Vt,
        "formulas_list": slr1.formulas_list,
        "first": first,
        "follow": follow,
        "dot_items": slr1.dot_items,
        "all_dfa": [dfa.to_dict() for dfa in slr1.all_DFA],
        "actions": new_actions,
        "gotos": new_gotos,
        "isSLR1": slr1.isSLR1,
        "SLR1_dot_str": slr1.dot
    }

    return jsonify({
        "code": 0,
        "data": data
    }), 200


@slr1_bp.route('/SLR1AnalyseInp', methods=['POST'])
def SLR1AnlyseInp():
    """SLR1 输入串分析"""
    data = request.get_json()
    text_list = data.get('inpProductions')
    inp_str = data.get('inpStr')
    slr1 = SLR1(text_list)
    slr1.init()
    slr1.solve(inp_str)

    # 处理First和Follow集合，将set类型转换为list类型以便JSON序列化
    first = slr1.first
    follow = slr1.follow
    for key in first:
        first[key] = list(first[key])
    for key in follow:
        follow[key] = list(follow[key])

    # 合并分析结果和First/Follow集合
    result_data = slr1.info.copy()
    result_data["first"] = first
    result_data["follow"] = follow

    return jsonify({
        "code": 0,
        "data": result_data
    }), 200
