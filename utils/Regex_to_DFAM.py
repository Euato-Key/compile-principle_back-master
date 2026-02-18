import copy
import time
import random

from graphviz import Digraph
from collections import defaultdict
from bidict import bidict


class NFA:
    def __init__(self, start, end):
        # both start and end are States
        self.start = start
        self.end = end


all_validate_State = {}  # { state.id : state }
nfa_state_id_map = bidict()  # 双向映射 { state.id : nfa_state.id }


class State:
    _id_counter = 0  # 自增id

    def __init__(self, isEnd):
        self.id = str(State._id_counter)
        State._id_counter += 1
        self.isEnd = isEnd  # isEnd is bool
        self.next_state = defaultdict(list)  # {'a':[state1, state2....],  'b':[state3]}
        self.before_state = defaultdict(set)  # {'a':{state1, state2....},  'b':{state3}}
        all_validate_State[self.id] = self


def is_valid_regex(regex):
    stack = []
    i = 0
    # 限定只存在于字符集中
    if not all(ch.strip() == ch and (32 <= ord(ch) <= 127 or ch == '•' or ch == 'ε') for ch in regex):
        print("存在非法字符！请仔细检查!")
        return False

    while i < len(regex):
        # 匹配成对括号
        if regex[i] == '(':
            stack.append('(')
        elif regex[i] == ')':
            if not stack:
                return False
            stack.pop()
        # | 左右两侧需要有有效字符或子表达式，并且不能在开头或结尾
        elif regex[i] == '|':
            if i == 0 or i == len(regex) - 1 \
                    or regex[i - 1] in ['(', '|', '•'] \
                    or regex[i + 1] in [')', '|', '*', '•']:
                return False
        # * 前面需要有有效字符或子表达式，且不能在开头
        elif regex[i] == '*':
            if i == 0 or regex[i - 1] in ['(', '|', '*', '•']:
                return False
        elif regex[i] == '•':
            if i == 0 or i == len(regex) - 1 \
                    or regex[i - 1] in ['(', '|', '•'] \
                    or regex[i + 1] in [')', '|', '*', '•']:
                return False
        i += 1
    # 增加对括号内为空或包含空括号的检查
    if stack:
        return False
    if '()' in regex:
        return False

    return True


def insert_concatenation(regex):
    result = ""
    i = 0
    while i < len(regex):
        if i < len(regex) - 1 and regex[i] not in ['(', '|', '•'] and regex[i + 1] not in [')', '|', '*', '•']:
            # 如果当前字符不是 (、|，且下一个字符不是 )、|、* ，则添加 • 作为连接符
            result += regex[i] + '•'
        else:
            result += regex[i]

        i += 1

    cins = []
    for ch in regex:
        if 32 <= ord(ch) <= 127 and ch not in ['(', ')', '*', '|', '•', 'ε']:
            cins.append(ch)
    cins.sort()
    return result, cins


def shunt(infix):
    """
        将正则表达式转换为后缀形式，便于提取运算优先级
        * = Zero or more
        • = Concatenation
        | =  Alternation
    :param infix: 正则表达式
    :return: 正则表达式的后缀形式
    """

    specials = {'*': 50, '•': 40, '|': 30}

    pofix = ""
    stack = ""

    # Loop through the string one character at a time
    for c in infix:
        if c == '(':
            stack = stack + c
        elif c == ')':
            while stack[-1] != '(':
                pofix, stack = pofix + stack[-1], stack[:-1]
            # Remove '(' from stack
            stack = stack[:-1]
        elif c in specials:
            while stack and specials.get(c, 0) <= specials.get(stack[-1], 0):
                pofix, stack = pofix + stack[-1], stack[:-1]
            stack = stack + c
        else:
            pofix = pofix + c

    while stack:
        pofix, stack = pofix + stack[-1], stack[:-1]

    return pofix


# ============================Thompson构造法： 正则表达式转换为NFA============================
def add_next_transition(come, to, symbol):
    # if symbol != 'ε' and len(come.next_state[symbol]) > 0:
    #     come.next_state[symbol].pop()
    # print(f"state{come.id} 添加其next state{to.id}")
    come.next_state[symbol].append(to)


def del_next_transtion(come, to, symbol):
    if to in come.next_state[symbol]:
        # print(f"state{come.id} 删除其next state{to.id}")
        come.next_state[symbol].remove(to)


def add_before_transition(to, come, symbol):
    # print(f"state{to.id} 添加其before state{come.id}")
    to.before_state[symbol].add(come)


def del_before_transition(to, come, symbol):
    if come in to.before_state[symbol]:
        # print(f"state{to.id} 删除其before state{come.id}")
        to.before_state[symbol].discard(come)


def fromEpsilon():  # 创建 1 --ε--> 2
    start = State(False)
    end = State(True)
    add_next_transition(start, end, 'ε')
    add_before_transition(end, start, 'ε')
    return start, end


def fromSymbol(symbol):  # 创建 1 --a--> 2
    start = State(False)
    end = State(True)
    add_next_transition(start, end, symbol)
    add_before_transition(end, start, symbol)
    return start, end


def clear_dead_state(dead_state_list):
    """
        清除all_validate_State变量中无用的State
    :param dead_state_list: 无用的State
    """
    # 清除Statee记录过的但当前已不存在连线的id
    global all_validate_State
    # print("待清除的state:",dead_state_list)
    to_del = []
    for state_id, state in all_validate_State.items():
        if state_id in dead_state_list:
            to_del.append(state_id)
    for to_del_item in to_del:
        del all_validate_State[to_del_item]


def union(first, second):  # a|b
    # start = State(False)
    # add_next_transition(start, first.start, 'ε')
    # add_next_transition(start, second.start, 'ε')
    #
    # end = State(True)
    # add_next_transition(first.end, end, 'ε')
    # first.end.isEnd = False
    # add_next_transition(second.end, end, 'ε')
    # second.end.isEnd = False

    first.end.isEnd = False
    second.end.isEnd = False
    # 合并first 和 second 的start
    start = State(False)
    # print(f"=====start======合并了:{first.start.id}")
    # print(f"=====start======合并了:{second.start.id}")
    for to_symbol, to_states in first.start.next_state.items():
        for to_state in to_states:
            add_next_transition(start, to_state, to_symbol)
            del_before_transition(to_state, first.start, to_symbol)
            add_before_transition(to_state, start, to_symbol)
    for to_symbol, to_states in second.start.next_state.items():
        for to_state in to_states:
            add_next_transition(start, to_state, to_symbol)
            del_before_transition(to_state, second.start, to_symbol)
            add_before_transition(to_state, start, to_symbol)

    # 合并first 和 second 的end
    end = State(True)
    # print(f"=====end======合并了:{first.end.id}")
    # print(f"=====end======合并了:{second.end.id}")
    for to_symbol, before_states in first.end.before_state.items():
        for before_state in before_states:
            del_next_transtion(before_state, first.end, to_symbol)
            add_next_transition(before_state, end, to_symbol)
            add_before_transition(end, before_state, to_symbol)
    for to_symbol, before_states in second.end.before_state.items():
        for before_state in before_states:
            del_next_transtion(before_state, second.end, to_symbol)
            add_next_transition(before_state, end, to_symbol)
            add_before_transition(end, before_state, to_symbol)

    clear_dead_state([first.start.id, first.end.id, second.start.id, second.end.id])

    return NFA(start, end)


def closure(nfa):  # a*
    start = State(False)
    end = State(True)

    # add_next_transition(start, end, 'ε')
    # add_next_transition(start, nfa.start, 'ε')
    #
    # add_next_transition(nfa.end, end, 'ε')
    # add_next_transition(nfa.end, nfa.start, 'ε')

    add_next_transition(start, nfa.start, 'ε')
    add_before_transition(nfa.start, start, 'ε')
    add_next_transition(nfa.start, end, 'ε')
    add_before_transition(end, nfa.start, 'ε')

    nfa.end.isEnd = False

    for to_symbol, before_states in nfa.end.before_state.items():
        for before_state in before_states:
            del_next_transtion(before_state, nfa.end, to_symbol)
            add_next_transition(before_state, nfa.start, to_symbol)
            add_before_transition(nfa.start, before_state, to_symbol)

    clear_dead_state([nfa.end.id])
    return NFA(start, end)


def concat(first, second):  # ab
    mid = State(False)
    # mid.next_state = copy.deepcopy(second.start.next_state)
    # mid.before_state = copy.deepcopy(first.end.before_state)

    for to_symbol, before_states in first.end.before_state.items():
        for before_state in before_states:
            del_next_transtion(before_state, first.end, to_symbol)
            add_next_transition(before_state, mid, to_symbol)
            add_before_transition(mid, before_state, to_symbol)
    for to_symbol, next_states in second.start.next_state.items():
        for next_state in next_states:
            del_before_transition(next_state, second.start, to_symbol)
            add_before_transition(next_state, mid, to_symbol)
            add_next_transition(mid, next_state, to_symbol)
    # first.end.id = second.start.id
    # first.end.isEnd = second.start.isEnd
    # first.end.next_state = second.start.next_state.copy()
    # 由于second（nfa）的start的before_state必为空，所以这里不用添加其before_state
    # first.end.isEnd = False

    # print("----------------:",first.end.id)
    # print([(ch, [x.id for x in s]) for ch, s in first.end.before_state.items()])
    # add_before_transition(first.end, first.start, )

    clear_dead_state([first.end.id, second.start.id])
    return NFA(first.start, second.end)


def Regex_to_NFA(postfix):
    """
        将regex转换为NFA
    :param postfix: regex的后缀形式
    :return:
        nfa: 由regex转换得到的NFA (NFA类：start, end)， 其中start和end都是State类
        dot.source: NFA图
    """
    if postfix == '':
        return fromEpsilon()
    stack = []
    for c in postfix:
        # print(c)
        if c == '•':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            new_nfa = concat(nfa1, nfa2)
            stack.append(new_nfa)
        elif c == '|':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            new_nfa = union(nfa1, nfa2)
            stack.append(new_nfa)
        elif c == '*':
            nfa = stack.pop()
            new_nfa = closure(nfa)
            stack.append(new_nfa)
        else:  # 是字符
            start, end = fromSymbol(c)
            stack.append(NFA(start, end))

    nfa = stack.pop()

    visited = []
    cnt = 0

    def dfs(state):
        nonlocal cnt
        if state in visited:
            return

        if cnt == 0:
            nfa_state_id_map[state.id] = 'X'
            cnt += 1
        elif state.isEnd:
            nfa_state_id_map[state.id] = 'Y'
        else:
            nfa_state_id_map[state.id] = str(cnt)
            cnt += 1

        visited.append(state)
        # print(
        #     f"========State: id={state.id}, isEnd={state.isEnd}=========\n next_state={[(ch, [x.id for x in s]) for ch, s in state.next_state.items()]} \n before_state={[(ch, [x.id for x in s]) for ch, s in state.before_state.items()]}\n")

        for to_states in state.next_state.values():
            for to_state in to_states:
                dfs(to_state)

    dfs(nfa.start)

    dot = Digraph(comment='NFA', graph_attr={'rankdir': 'LR'})
    # 画节点
    for state in visited:
        # print(f"state:{nfa_state_id_map[state.id]}, isEnd={state.isEnd}", end="")
        node_color = 'red' if state.isEnd or nfa_state_id_map[state.id] == 'X' else 'black'
        node_shape = 'doublecircle' if state.isEnd else 'circle'
        dot.node(name=nfa_state_id_map[state.id], label=nfa_state_id_map[state.id], color=node_color, shape=node_shape)
        # for to_symbol, to_states in state.next_state.items():
        #     for to_state in to_states:
        #         print(f"  经过{to_symbol}到达{nfa_state_id_map[to_state.id]}", end="")
        # print()
    # 画边
    for state in visited:
        for to_symbol, to_states in state.next_state.items():
            for to_state in to_states:
                dot.edge(tail_name=nfa_state_id_map[state.id], head_name=nfa_state_id_map[to_state.id], label=to_symbol)
    # 增加开始标志
    dot.node(name="start", label="", color="white")
    dot.edge(tail_name="start", head_name="X", label="start")
    # print([id for id in all_validate_State.keys()])
    # for id, state in all_validate_State.items():
    #     print(
    #         f"========State: id={id}, isEnd={state.isEnd}=========\n next_state={[(ch, [x.id for x in s]) for ch, s in state.next_state.items()]} \n before_state={[(ch, [x.id for x in s]) for ch, s in state.before_state.items()]}\n")
    #
    # for id, state in all_validate_State.items():
    #     print(f"state:{id}, isEnd={state.isEnd}", end="")
    #     node_color = 'red' if state.isEnd else 'black'
    #     node_shape = 'doublecircle' if state.isEnd else 'circle'
    #     node_label = 'Y' if state.isEnd else ('X' if nfa_state_id_map[state.id] == '0' else nfa_state_id_map[state.id])
    #     dot.node(name=id, label=node_label, color=node_color, shape=node_shape)
    #     for to_symbol, to_states in state.next_state.items():
    #         for to_state in to_states:
    #             print(f"  经过{to_symbol}到达{to_state.id}", end="")
    #     print()
    #
    # for id, state in all_validate_State.items():
    #     for to_symbol, to_states in state.next_state.items():
    #         for to_state in to_states:
    #             dot.edge(tail_name=id, head_name=to_state.id, label=to_symbol)

    # print(dot.source)
    # dot.view()
    return nfa, dot.source


# ============================子集法 确定DFA============================
def ε_closure(nfa_state_ids):
    """
        I = ε_closure(States) , 即 States 经过 若干个ε 可到达的 State 的集合
    :param nfa_state_ids: 状态集合，[1,2,3...]
    :return: I ，[1,2,3...]
    """
    res = list(nfa_state_ids)
    visited = []

    # print(nfa_state_id_map)
    def dfs(state):
        if state in visited:
            return
        visited.append(state)
        for next_state in state.next_state['ε']:
            if nfa_state_id_map[next_state.id] not in res:
                res.append(nfa_state_id_map[next_state.id])
            dfs(next_state)

    for id in nfa_state_ids:
        dfs(all_validate_State[nfa_state_id_map.inverse[id]])

    def sortStates(x):
        if str(x).isdigit():
            return (0, int(x))
        else:
            return (1, x)

    res.sort(key=sortStates)
    return res


def J_a(nfa_state_ids, ch):
    """
        J_a 为 States 仅经过1个 a 可到达的 State 的集合
    :param nfa_state_ids:  状态集合，[1,2,3...]
    :param ch:  跳转字符
    :return:  J_a ， [1,2,3...]
    """
    res = list()

    for id in nfa_state_ids:
        for next_state in all_validate_State[nfa_state_id_map.inverse[id]].next_state[ch]:
            if nfa_state_id_map[next_state.id] not in res:
                res.append(nfa_state_id_map[next_state.id])

    def sortStates(x):
        if str(x).isdigit():
            return (0, int(x))
        else:
            return (1, x)

    res.sort(key=sortStates)
    return res


# 利用子集法 将NFA确定化为 状态转换矩阵
def NFA_to_DFA(nfa,cins):
    """
    NFA转换DFA
    :param nfa: 由regex转换得到的NFA (NFA类：start, end)， 其中start和end都是State类
    :param cins: 输入字符， 列表类型, ['a','b']
    :return:
        table: 转换表，dict形式，表格内容是 各个ε_closure(J)子集法求得的集合 { 'I': [{'1','2','3'}...]....}
        table_to_num:  状态转换矩阵，dict形式，表格内容是 DFA状态序号  { 'I': ['1','2','3']....}
        initial_states: DFA初态集合，dict形式，序号映射NFA状态集，{'2': {'Y','3'}}
        termination_states: DFA终态集合，dict形式，序号映射NFA状态集，{'2': {'Y','3'}}
        transition_map: DFA各个状态的转换关系，dict形式，{'0': {'a': '1'} }
        dot.source: DFA图
    """

    table = {
        "I": [],
    }
    # ==============确定列名==============
    for ch in cins:
        table['I' + ch] = []
    # print(table)

    # ==============迭代填充转换表==============
    new_states_list = [ε_closure({nfa_state_id_map[nfa.start.id]})]
    table["I"] = [ε_closure({nfa_state_id_map[nfa.start.id]})]
    delta_news_state_list = [ε_closure({nfa_state_id_map[nfa.start.id]})]  # 存储每次新增的 new_states
    while len(delta_news_state_list) > 0:
        delta_news_state_list_copy = copy.deepcopy(delta_news_state_list)  # 拷贝 新增列表
        delta_news_state_list = []  # 重置 新增列表
        for states in delta_news_state_list_copy:  # I列新增的 states
            for key in table.keys():  # 填充I列中各个 states 的 Ia 和 Ib
                if key == 'I':
                    continue
                # print(J_a(states, key[1:]))
                res = ε_closure(J_a(states, key[1:]))
                # print(f"{states}  {'I' + key[1:]} ---{res} ")

                table[key].append(res)
                if res not in new_states_list and len(res) > 0:
                    delta_news_state_list.append(res)
                    new_states_list.append(res)
                    table['I'].append(res)

    # ==============将转换表里的集合元素 转换为 序号，并确定出初态和终态集合==============
    table_to_num = {}  # 转换矩阵
    initial_states = {}  # 初态集合 字典映射形式 num: states ==>  {'2': {'Y','3'}}
    termination_states = {}  # 终态集合 字典映射形式 num: states  ==>  {'2': {'Y','3'}}

    for key in table.keys():
        if key == 'I':
            table_to_num[key] = [str(i) for i in range(len(table[key]))]
        else:
            table_to_num[key] = ["" for i in range(len(table[key]))]  # 初始化为空集
    for I_idx, I_states in enumerate(table["I"]):
        for key in table.keys():
            if key == 'I':
                continue
            to_change = []
            for ch_idx, ch_states in enumerate(table[key]):
                if I_states == ch_states:
                    to_change.append(ch_idx)
            for change_idx in to_change:
                table_to_num[key][change_idx] = str(I_idx)

    for idx, states in enumerate(table['I']):
        if 'Y' in states:
            termination_states[str(idx)] = states
        if 'X' in states:
            initial_states[str(idx)] = states

    # print(table)
    # print("initial_states=",initial_states)

    # ==============画图: 转换表对应的DFA， 并记录transition==============
    dot = Digraph(comment='DFA_waitToMin', graph_attr={'rankdir': 'LR'})
    for state_id in table_to_num["I"]:
        node_color = 'red' if state_id in termination_states.keys() or state_id in initial_states.keys() else 'black'
        node_shape = 'doublecircle' if state_id in termination_states.keys() else 'circle'
        dot.node(name=state_id, label=state_id, color=node_color, shape=node_shape)

    transition_map = {}  # { '0': { 'a': '1' } }
    for state_id in table_to_num['I']:
        transition_map[state_id] = {}
    for idx, state_id in enumerate(table_to_num["I"]):
        for key in table_to_num.keys():
            if key == 'I':
                continue
            if table_to_num[key][idx] == "":
                continue
            dot.edge(tail_name=state_id, head_name=table_to_num[key][idx], label=key[1:])
            transition_map[state_id][key[1:]] = table_to_num[key][idx]

    dot.node(name="start", label="", color='white')
    for key in initial_states.keys():
        dot.edge(tail_name="start", head_name=key, label="start")
    # print(dot.source)
    # dot.view()

    # 修改key值："I"改成“S”，“Ia”改成“a”....
    for key in list(table_to_num.keys()):
        if key == 'I':
            table_to_num['S'] = table_to_num.pop(key)
        else:
            table_to_num[key[1:]] = table_to_num.pop(key)

    # print(table_to_num.keys())
    return table, table_to_num, initial_states, termination_states, transition_map, dot.source


# ============================hopcroft算法 最小化DFA============================
def hopcroft_algorithm(total_states, termination_states, state_transition_map, cins):
    """
    :param total_states: DFA所有状态
    :param termination_states: DFA终态
    :param state_transition_map:  DFA状态转换关系
    :param cins:  字符
    :return:
        P: 不可再分的状态集合， [ {} , {} ...]
        P_change： 存储P的变化过程 [ [ {} , {} ] , [ {} ] ..]
    """
    cins = set(cins)
    termination_states = set(termination_states)
    total_states = set(total_states)
    state_transition_map = state_transition_map
    not_termination_states = total_states - termination_states

    def get_source_set(target_set, char):
        source_set = set()
        for state in total_states:
            try:
                if state_transition_map[state][char] in target_set:
                    source_set.update(state)
            except KeyError:
                pass
        return source_set

    if len(not_termination_states) > 0:  # not_termination_states可能为空，防止后续程序出错
        P = [termination_states, not_termination_states]
        W = [termination_states, not_termination_states]
    else:
        P = [termination_states]
        W = [termination_states]

    P_change = [P]  # 存储P_temp，查看中间变化过程
    random.seed(1)
    while W:
        A = random.choice(W)
        W.remove(A)

        for char in cins:
            X = get_source_set(A, char)
            P_temp = []

            for Y in P:
                S = X & Y
                S1 = Y - X

                if len(S) and len(S1):
                    P_temp.append(S)
                    P_temp.append(S1)

                    if Y in W:
                        W.remove(Y)
                        W.append(S)
                        W.append(S1)
                    else:
                        if len(S) <= len(S1):
                            W.append(S)
                        else:
                            W.append(S1)
                else:
                    P_temp.append(Y)
            if P_temp not in P_change:
                P_change.append(P_temp)
            P = copy.deepcopy(P_temp)


    return P, P_change


def Min_DFA(table_to_num, initial_states, termination_states, transition_map, cins):
    """
    最小化DFA
    :param table:  转换表，dict形式，表格内容是 各个ε_closure(J)子集法求得的集合
    :param table_to_num: 状态转换矩阵，dict形式，表格内容是 DFA状态序号
    :param initial_states: DFA初态集合，dict形式，序号映射NFA状态集，{'2': {'Y','3'}}
    :param termination_states:  DFA终态集合，dict形式，序号映射NFA状态集，{'2': {'Y','3'}}
    :param transition_map: DFA各个状态的转换关系，dict形式，{'0': {'a': '1'} }
    :param cins: 输入字符， 列表类型, ['a','b']
    :return:
        P: 不可再分的状态集合， [ {} , {} ...]
        P_change： 存储P的变化过程 [ [ {} , {} ] , [ {} ] ..]
        dot.source: NFA图
    """
    P, P_change = hopcroft_algorithm(table_to_num['S'], termination_states.keys(), transition_map, cins)
    for i in range(len(P)):
        P[i] = list(P[i])
        P[i].sort()

    for i in range(len(P_change)):
        for j in range(len(P_change[i])):
            P_change[i][j] = list(P_change[i][j])
            P_change[i][j].sort()

    # print("P=", P)
    P.sort(key=lambda x: min(x))  # 排序，方便查看
    for p in P_change:
        p.sort(key=lambda x: min(x))  # 排序，方便查看
    # print("P=", P)
    new_states = []
    new_states_map = {}
    new_initial_states = []
    new_termination_states = []
    new_transtion_map = {}

    for idx, states in enumerate(P):
        new_states.append(str(idx))
        new_states_map[str(idx)] = states
        if states[0] in initial_states.keys():
            new_initial_states.append(str(idx))
        if states[0] in termination_states.keys():
            new_termination_states.append(str(idx))

        new_transtion_map[str(idx)] = transition_map[states[0]]

    # print("new_transtion_map：", new_transtion_map)

    for new_state_id, transitions in new_transtion_map.items():
        for to_symbol, next_state in transitions.items():
            for new_state_id2, old_states in new_states_map.items():
                if next_state in old_states:
                    new_transtion_map[new_state_id][to_symbol] = new_state_id2

    # print("new_states：", new_states)
    # print("new_initial_states：", new_initial_states)
    # print("new_termination_states：", new_termination_states)
    # print("new_transtion_map：", new_transtion_map)

    table_to_num_min = {} # 最小化DFA 的 状态转换表
    for key in table_to_num.keys():
        if key == 'S':
            table_to_num_min[key] = [str(i) for i in range(len(new_states))]
        else:
            table_to_num_min[key] = ["" for i in range(len(new_states))]


    dot = Digraph(comment='DFA', graph_attr={'rankdir': 'LR'})
    for state_id in new_states:
        node_color = 'red' if state_id in new_termination_states or state_id in initial_states else 'black'
        node_shape = 'doublecircle' if state_id in new_termination_states else 'circle'
        dot.node(name=state_id, label=state_id, color=node_color, shape=node_shape)

    for state_id, transitons in new_transtion_map.items():
        for to_symbol, next_state in transitons.items():
            dot.edge(tail_name=state_id, head_name=next_state, label=to_symbol)
            table_to_num_min[to_symbol][int(state_id)] = next_state

    dot.node(name="start", label="", color='white')
    for state_id in initial_states:
        dot.edge(tail_name="start", head_name=state_id, label="start")
    # print("table_to_num_min",table_to_num_min)
    # print(dot.source)
    # print(type(dot.source))
    # dot.view()

    return P, P_change, table_to_num_min, dot.source


if __name__ == '__main__':
    regex = ' \t\n(ad|b)*c'  # 不接受空白字符
    regex = '(ad|b)*c'
    # regex = '(a(c|d)|a(a|b))'
    # regex = 'a((c|d)|(a|b))'
    # regex = 'abc|de|f'
    # regex = '((a).b.(c))'
    # regex = 'a|b*|c'

    # regex = 'b*(d|ad)(b|ab)(b|ab)*' # 例2.6
    # regex = '(a|b)*(aa|bb)(a|b)*'  # 例2.8
    # regex = '(a|b)*' # 例2.10
    # regex = '(a*b*)*' # 例2.10
    # regex = 'a*b*' # 例2.10
    # regex = '(cc*:|ε)cc*(.cc*|ε)' # 例2.11
    # regex = 'dd*(.dd*|ε)(e(+|-|ε)dd*|ε)' # 例2.12
    # regex = 'b*(abb*)*' # 例2.13
    # regex = 'b*a(b|ab*a)*' # 例 2.14

    if is_valid_regex(regex):
        regex, cins = insert_concatenation(regex)
        profix = shunt(regex)
        # print("后缀表达式", profix)

        nfa, NFA_dot_str= Regex_to_NFA(profix)

        table, table_to_num, initial_states, termination_states, transition_map, DFA_dot_str = NFA_to_DFA(nfa, cins)
        # print(f"=======转换表======")
        # for key in table.keys():
        #     print(f"{key}\t", end="")
        # print()
        # for idx in range(len(table["I"])):
        #     for key in table.keys():
        #         print(f"{table[key][idx]}\t", end="")
        #     print()
        # for key, value in table_to_num.items():
        #     print(f"{key}  ===== {value}")

        P, P_change, table_to_num_min, Min_DFA_dot_str = Min_DFA(table_to_num, initial_states, termination_states, transition_map, cins)
        print(P_change)
    else:
        print("不合法的表达式！")
