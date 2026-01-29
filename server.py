from Class_LL1_GrammarAnalysis import LL1
from Class_LR0_GrammarAnalysis import LR0
from Class_SLR1_GrammarAnalysis import SLR1
import Regex_to_DFAM as RF

from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from bidict import bidict

app = Flask(__name__)
CORS(app)

# ================= 反爬核心配置 =================
def get_real_ip():
    """
    安全获取经过代理的真实客户端IP
    优先级：X-Forwarded-For -> X-Real-IP -> 默认remote_address
    """
    print("=========================================================",request.headers.get('X-Real-IP', get_remote_address()))
    forwarded_for = request.headers.get('X-Forwarded-For', '').split(',')
    if forwarded_for and len(forwarded_for) > 0:
        # 取第一个非内网IP（根据实际网络结构调整过滤逻辑）
        for ip in forwarded_for:
            ip = ip.strip()
            if not ip.startswith(('10.', '172.16.', '192.168.')):
                return ip
        return forwarded_for[0].strip()
    return request.headers.get('X-Real-IP', get_remote_address())

# 初始化限流器（生产环境建议使用Redis存储）
limiter = Limiter(
    app=app,
    key_func=get_real_ip,  # 基于真实客户端IP
    default_limits=["2000 per day", "500 per hour"],  # 全局默认限制
    storage_uri="memory://",  # 限流计数器的存储后端， 默认未内存存储， 生产环境建议改为redis://
    strategy="fixed-window-elastic-expiry"  # 限流策略： 弹性窗口策略
)

# ================= 路由保护配置 =================
@app.errorhandler(429)
def ratelimit_handler(e):
    """自定义限流响应"""
    return jsonify({
        "code": 429,
        "msg": "请求过于频繁，请稍后再试"
    }), 429

@app.errorhandler(500)
def server_error(error):
    return '服务异常'


# ================= 接口配置 =================
@app.route('/api/test', methods=['GET'])
@limiter.limit("3/minute")
def test():
    return jsonify({
        "code": 0,
        "msg": "test success!"
    }), 200


@app.route('/api/LL1Analyse', methods=['POST'])
@limiter.limit("1000/minute")
def LL1anlyse():
    data = request.get_json()
    text_list = data.get('inpProductions')
    # print(text_list)
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
    # print(new_table)

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

    # print(data)
    return jsonify({
        "code": 0,
        "data": data
    }), 200


@app.route('/api/LL1AnalyseInp', methods=['POST'])
@limiter.limit("1000/minute")
def LL1AnlyseInp():
    data = request.get_json()
    text_list = data.get('inpProductions')
    inp_str = data.get('inpStr')
    ll1 = LL1(text_list)
    ll1.init()
    ll1.solve(inp_str)
    # print(ll1.info)
    return jsonify({
        "code": 0,
        "data": ll1.info
    }), 200


@app.route('/api/LR0Analyse', methods=['POST'])
@limiter.limit("1000/minute")
def LR0Anlyse():
    data = request.get_json()
    text_list = data.get('inpProductions')
    # print(text_list)
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

    # print(data)
    return jsonify({
        "code": 0,
        "data": data
    }), 200


@app.route('/api/LR0AnalyseInp', methods=['POST'])
@limiter.limit("1000/minute")
def LR0AnlyseInp():
    data = request.get_json()
    text_list = data.get('inpProductions')
    inp_str = data.get('inpStr')
    lr0 = LR0(text_list)
    lr0.init()
    lr0.solve(inp_str)
    # print(lr0.info)
    return jsonify({
        "code": 0,
        "data": lr0.info
    }), 200


@app.route('/api/SLR1Analyse', methods=['POST'])
@limiter.limit("1000/minute")
def SLR1Anlyse():
    data = request.get_json()
    text_list = data.get('inpProductions')
    # print(text_list)
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

    # print(data)
    return jsonify({
        "code": 0,
        "data": data
    }), 200


@app.route('/api/SLR1AnalyseInp', methods=['POST'])
@limiter.limit("1000/minute")
def SLR1AnlyseInp():
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
    
    # print(slr1.info)
    return jsonify({
        "code": 0,
        "data": result_data
    }), 200


@app.route('/api/Regex_to_DFAM', methods=['POST'])
@limiter.limit("3000/minute")
def Regex_to_DFAM():
    data = request.get_json()
    regex = data.get('inpRegex')
    # print(regex)
    # regex = '(ad|b)*c'
    if RF.is_valid_regex(regex):
        RF.all_validate_State={}
        RF.nfa_state_id_map=bidict()
        RF.State._id_counter = 0

        regex, cins =RF.insert_concatenation(regex)
        profix = RF.shunt(regex)
        nfa, NFA_dot_str = RF.Regex_to_NFA(profix)
        table, table_to_num, initial_states, termination_states, transition_map, DFA_dot_str = RF.NFA_to_DFA(nfa,cins)
        P, P_change, table_to_num_min, Min_DFA_dot_str = RF.Min_DFA(table_to_num, initial_states, termination_states, transition_map,cins)

        return jsonify({
            "code": 0,
            "data": {
                'table': table, # NFA->DFA 的 转换表（子集法）
                'table_to_num': table_to_num, # NFA->DFA 的 状态转换表
                'table_to_num_min': table_to_num_min, # 最小化DFA 的 状态转换表
                'P': P, # 最小化DFA 的 结果
                'P_change': P_change, # 最小化DFA的结果 的 迭代过程
                'NFA_dot_str': NFA_dot_str, # 绘制NFA的dot
                'DFA_dot_str': DFA_dot_str, # 绘制DFA的dot
                'Min_DFA_dot_str': Min_DFA_dot_str, # 绘制最小化DFA的dot
            }
        }), 200
    else:
        return jsonify({
            "code": 1,
            "message": "不合规的正则表达式，请重新输入！"
        }), 200


if __name__ == '__main__':
    print("!!!!!!!!!!!!startup!!!!!!!!!!!!!!!")
    app.run(host='0.0.0.0')
