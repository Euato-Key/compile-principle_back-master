"""
FA (Finite Automaton) 有限自动机相关接口蓝图
包含正则表达式转 NFA、DFA、最小化 DFA 等功能
"""
from flask import Blueprint, request, jsonify
from bidict import bidict
import utils.Regex_to_DFAM as RF

fa_bp = Blueprint('fa', __name__, url_prefix='/api')


@fa_bp.route('/Regex_to_DFAM', methods=['POST'])
def Regex_to_DFAM():
    """正则表达式转 NFA/DFA/最小化DFA"""
    data = request.get_json()
    regex = data.get('inpRegex')
    
    if RF.is_valid_regex(regex):
        RF.all_validate_State = {}
        RF.nfa_state_id_map = bidict()
        RF.State._id_counter = 0

        regex, cins = RF.insert_concatenation(regex)
        profix = RF.shunt(regex)
        nfa, NFA_dot_str = RF.Regex_to_NFA(profix)
        table, table_to_num, initial_states, termination_states, transition_map, DFA_dot_str = RF.NFA_to_DFA(nfa, cins)
        P, P_change, table_to_num_min, Min_DFA_dot_str = RF.Min_DFA(table_to_num, initial_states, termination_states, transition_map, cins)

        return jsonify({
            "code": 0,
            "data": {
                'table': table,  # NFA->DFA 的 转换表（子集法）
                'table_to_num': table_to_num,  # NFA->DFA 的 状态转换表
                'table_to_num_min': table_to_num_min,  # 最小化DFA 的 状态转换表
                'P': P,  # 最小化DFA 的 结果
                'P_change': P_change,  # 最小化DFA的结果 的 迭代过程
                'NFA_dot_str': NFA_dot_str,  # 绘制NFA的dot
                'DFA_dot_str': DFA_dot_str,  # 绘制DFA的dot
                'Min_DFA_dot_str': Min_DFA_dot_str,  # 绘制最小化DFA的dot
            }
        }), 200
    else:
        return jsonify({
            "code": 1,
            "message": "不合规的正则表达式，请重新输入！"
        }), 200
