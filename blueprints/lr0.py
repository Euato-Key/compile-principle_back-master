"""
LR0 语法分析相关接口蓝图
包含 LR0 文法分析和输入串分析功能
"""
from flask import Blueprint, request, jsonify
from utils.Class_LR0_GrammarAnalysis import LR0

lr0_bp = Blueprint('lr0', __name__, url_prefix='/api')


@lr0_bp.route('/LR0Analyse', methods=['POST'])
def LR0Anlyse():
    """LR0 文法分析"""
    data = request.get_json()
    text_list = data.get('inpProductions')
    lr0 = LR0(text_list)
    lr0.init()

    # dist<tuple , str>， 其中key为tuple类型，不好转换json，将其转为str类型
    actions = lr0.actions
    gotos = lr0.gotos
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

    data = {
        "S": lr0.S,
        "Vn": lr0.Vn,
        "Vt": lr0.Vt,
        "formulas_list": lr0.formulas_list,
        "dot_items": lr0.dot_items,
        "all_dfa": [dfa.to_dict() for dfa in lr0.all_DFA],
        "actions": new_actions,
        "gotos": new_gotos,
        "isLR0": lr0.isLR0,
        "LR0_dot_str": lr0.dot
    }

    return jsonify({
        "code": 0,
        "data": data
    }), 200


@lr0_bp.route('/LR0AnalyseInp', methods=['POST'])
def LR0AnlyseInp():
    """LR0 输入串分析"""
    data = request.get_json()
    text_list = data.get('inpProductions')
    inp_str = data.get('inpStr')
    lr0 = LR0(text_list)
    lr0.init()
    lr0.solve(inp_str)
    return jsonify({
        "code": 0,
        "data": lr0.info
    }), 200
