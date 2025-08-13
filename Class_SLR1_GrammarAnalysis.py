import copy
from collections import defaultdict
# import graphviz
import graphviz
import pandas as pd


class DFA:
    def __init__(self, id_, pros_, next_ids_):
        self.id_ = id_  # number, 编号
        self.pros_ = pros_  # list, productions
        self.next_ids_ = next_ids_  # dist, { v1:id1 , v2:id2 ...}

    def to_dict(self):
        return {
            'id': self.id_,
            'pros': self.pros_,
            'next_ids': self.next_ids_
        }

    def __eq__(self, other):
        return set(self.pros_) == set(other.pros_)


class FirstAndFollow:
    def __init__(self, formulas_list):
        self.formulas_list = formulas_list
        self.formulas_dict = defaultdict(set)
        self.first = defaultdict(set)
        self.follow = defaultdict(set)
        self.S = ""
        self.Vn = set()
        self.Vt = set()
        self.info = {}

    def process(self, formulas_list):
        formulas_dict = defaultdict(set)  # 存储产生式 ---dict<set> 形式
        # 转为特定类型
        for production in formulas_list:
            left, right = production.split('->')
            if "|" in right:
                r_list = right.split("|")
                for r in r_list:
                    formulas_dict[left].add(r)
            else:
                formulas_dict[left].add(right)  # 若left不存在，会自动创建 left: 空set

        S = list(formulas_dict.keys())[0]  # 文法开始符
        Vn = set()
        Vt = set()
        for left, right in formulas_dict.items():  # 获取终结符和非终结符
            Vn.add(left)
            for r_candidate in right:
                for symbol in r_candidate:
                    if not symbol.isupper() and symbol != 'ε':
                        Vt.add(symbol)

        # print(formulas_dict)
        # print(S)
        # print(Vn)
        # print(Vt)
        return formulas_dict, S, Vn, Vt

    def cal_v_first(self, v):  # 计算符号v的first集
        # 如果是终结符或ε，直接加入到First集合
        if not v.isupper():
            self.first[v].add(v)
        else:
            for r_candidate in self.formulas_dict[v]:
                i = 0

                while i < len(r_candidate):
                    next_symbol = r_candidate[i]
                    # 如果是非终结符，递归计算其First集合
                    if next_symbol.isupper():
                        if next_symbol == v:  # -----若相同，则为直接左递归，直接跳出-----
                            break
                        self.cal_v_first(next_symbol)  # -----遇到间接左递归，容易递归爆栈-----
                        self.first[v] = self.first[v].union(self.first[next_symbol] - {'ε'})  # 合并first(next_symbol)/{ε}
                        if 'ε' not in self.first[next_symbol]:
                            break
                    # 如果是终结符，加入到First集合
                    else:
                        self.first[v].add(next_symbol)
                        break
                    i += 1
                # 如果所有符号的First集合都包含ε，将ε加入到First集合
                if i == len(r_candidate):
                    self.first[v].add('ε')

    def cal_all_first(self):  # ！！！！！！！！！只计算非终结符的first集！！！！！！！！
        for vn in self.formulas_dict.keys():
            self.cal_v_first(vn)
        for vt in self.Vt:
            self.cal_v_first(vt)
        self.cal_v_first('ε')

    # def: 计算Follow集合1——考虑 添加first(Vn后一个非终结符)/{ε}， 而 不考虑 添加follow(left)
    def cal_follow1(self, vn):
        self.follow[vn] = set()
        if vn == self.S:  # 若为开始符，加入#
            self.follow[vn].add('#')
        for left, right in self.formulas_dict.items():  # 遍历所有文法，取出左部单Vn、右部候选式集合
            for r_candidate in right:  # 遍历当前 右部候选式集合
                i = 0
                while i <= len(r_candidate) - 1:  # 遍历当前 右部候选式
                    if r_candidate[i] == vn:  # ch == Vn
                        if i + 1 == len(r_candidate):  # 如果是最后一个字符  >>>>>  S->....V
                            self.follow[vn].add('#')
                            break
                        else:  # 后面还有字符  >>>>> S->...V..
                            while i != len(r_candidate):
                                i += 1
                                # if r_candidate[i] == vn:  # 又遇到Vn，回退 >>>>> S->...V..V..
                                #     break
                                if r_candidate[i].isupper():  # 非终结符  >>>>> S->...VA..
                                    self.follow[vn] = self.follow[vn].union(self.first[r_candidate[i]] - {'ε'})
                                    if 'ε' in self.first[r_candidate[i]]:  # 能推空  >>>>> S->...VA..  A可推空
                                        if i + 1 == len(r_candidate):  # 是最后一个字符  >>>>> S->...VA  A可推空 可等价为 S->...V
                                            self.follow[vn].add('#')
                                            break
                                    else:  # 不能推空 >>>>> S->...VA..  A不可推空
                                        break
                                else:  # 终结符  >>>>> S->...Va..
                                    self.follow[vn].add(r_candidate[i])
                                    break
                    else:
                        i += 1

    # def: 计算Follow集合2——考虑 添加follow(left)
    def cal_follow2(self, vn):
        for left, right in self.formulas_dict.items():  # 遍历所有文法，取出左部单Vn、右部候选式集合
            for r_candidate in right:  # 遍历当前 右部候选式集合
                i = 0
                while i <= len(r_candidate) - 1:  # 遍历当前 右部候选式
                    if r_candidate[i] == vn:  # 找到Vn
                        if i == len(r_candidate) - 1:  # 如果当前是最后一个字符，添加 follow(left) >>>>>  S->..V
                            self.follow[vn] = self.follow[vn].union(self.follow[left])
                            break
                        else:  # 看看后面的字符能否推空 >>>>>  S->..V..
                            while i != len(r_candidate):
                                i += 1
                                if 'ε' in self.first[r_candidate[i]]:  # 能推空  >>>>> S->..VB..  B可推空
                                    if i == len(r_candidate) - 1:  # 且是最后一个字符  >>>>> S->..VB  B可推空
                                        self.follow[vn] = self.follow[vn].union(self.follow[left])
                                        break
                                    else:  # 不是最后一个字符，继续看  >>>>> S->..VBA..  B可推空
                                        continue
                                else:  # 不能推空  >>>>>  S->..VB..  B不可为空
                                    break
                    i += 1

    # def: 计算所有Follow集合的总长度，用于判断是否还需要继续完善
    def cal_follow_total_Len(self):
        total_Len = 0
        for vn, vn_follow in self.follow.items():
            total_Len += len(vn_follow)
        return total_Len

    def cal_all_follow(self):
        # 先用 cal_follow1 算
        for vn in self.formulas_dict.keys():
            self.cal_follow1(vn)

        # 在循环用 cal_follow2 算， 直到所有follow集总长度不再变化，说明计算完毕
        while True:
            old_len = self.cal_follow_total_Len()
            for vn in self.formulas_dict.keys():
                self.cal_follow2(vn)
            new_len = self.cal_follow_total_Len()
            if old_len == new_len:
                break

    def solve(self):
        # print("\n=============FirstFollow=============")
        self.formulas_dict, self.S, self.Vn, self.Vt = self.process(self.formulas_list)
        self.cal_all_first()
        self.cal_all_follow()
        # print(f"first: {self.first}")
        # print(f"follow: {self.follow}")
        # print("=============FirstFollow=============\n")

        return self.first, self.follow


class SLR1:
    def __init__(self, formulas_list):
        self.formulas_list = formulas_list  # 存储产生式  ---list形式
        self.S = ""
        self.Vn = []
        self.Vt = []
        self.dot_items = []  # 所有可能的.项目集
        self.dot = ""
        self.all_DFA = []
        self.actions = {}
        self.gotos = {}
        self.first = defaultdict(set)
        self.follow = defaultdict(set)
        self.info = {}
        self.isSLR1 = False

    def step1_pre_process(self, grammar_list):
        formulas_list = []
        S = grammar_list[0][0]  # 开始符
        Vt = []  # 终结符
        Vn = []  # 非终结符
        # 处理产生式
        for pro in grammar_list:
            pro_left, pro_right = pro.split("->")
            if "|" in pro_right:
                r_list = pro_right.split("|")
                for r in r_list:
                    formulas_list.append(pro_left + "->" + r)
            else:
                formulas_list.append(pro)

        # 增广文法
        formulas_list.insert(0, S + "'->" + S)
        # print(formulas_list)

        # 处理Vn和Vt
        for pro in formulas_list:
            pro_left, pro_right = pro.split("->")
            if pro_left not in Vn:
                Vn.append(pro_left)
            for r_candidate in pro_right:
                for symbol in r_candidate:
                    if not symbol.isupper() and symbol != 'ε':
                        if symbol not in Vt:
                            Vt.append(symbol)

        # print("Vn:", Vn)
        # print("Vt:", Vt)

        ff = FirstAndFollow(formulas_list)
        first, follow = ff.solve()
        return S, Vn, Vt, formulas_list, first, follow

    def step2_all_dot_pros(self, grammar_str):
        dot_items = []
        for pro in grammar_str:
            dor_left, dot_right = pro.split('->')
            if dot_right == 'ε':
                dot_items.append(dor_left + "->.")
                continue
            ind = pro.find("->")  # 返回-的下标
            for i in range(len(pro) - ind - 1):
                tmp = pro[:ind + 2 + i] + "." + pro[ind + 2 + i:]
                dot_items.append(tmp)

        return dot_items

    def closure(self, item):  # 求item所有的产生式的闭包
        c_item = item
        old_c_item = []
        while len(old_c_item) != len(c_item):
            old_c_item = copy.deepcopy(c_item)
            for pro in old_c_item:
                if pro not in c_item:
                    c_item.append(pro)
                dot_left, dot_right = pro.split(".")
                if dot_right == "":  # 当前产生式为最后一项为. .不能继续移动，跳过
                    continue
                if dot_right[0] in self.Vn:  # .后面为非终结符， 加入它的Vn->.xxxx
                    for dot_p in self.dot_items:
                        ind = dot_p.find("->")  # 返回-的下标
                        if dot_p[0] == dot_right[0] \
                                and dot_p[ind + 2] == "." \
                                and dot_p[1] != "'" \
                                and dot_p not in c_item:  # 首字符匹配 且不为增广符
                            c_item.append(dot_p)

        return c_item

    def go(self, item, v):  # 生成item向v移动后的item_production
        to_v_item = []
        for pro in item:  # 1. 生成item能够用v跳转的新的产生式
            dot_left, dot_right = pro.split(".")
            if dot_right != "":  # 非归约/接受项目
                if dot_right[0] == v:  # .右边是跳转符v
                    to_v_item.append(dot_left + dot_right[0] + "." + dot_right[1:])  # 右移一位

        new_item = None
        if len(to_v_item) != 0:  # 2. 求新产生式的闭包
            new_item = self.closure(to_v_item)

        return new_item

    def exist_idx(self, all_DFA, new_dfa):
        if new_dfa.pros_ is None:
            return -1
        for i in range(len(all_DFA)):
            if new_dfa == all_DFA[i]:
                return i
        return -1

    def step3_construct_SLR1_DFA(self, dot_items):
        # 生成初始Item0
        all_DFA = []
        item0_pros = []
        item0_pros.extend(self.closure([dot_items[0]]))
        all_DFA.append(DFA(0, item0_pros, {}))

        visited_dfa = []  # close表
        old_visted_dfa = []  # 用于判断close表长度是否再变化

        V = list(self.Vn) + list(self.Vt)  # 合并非终结符和终结符
        while True:
            old_visted_dfa = copy.deepcopy(visited_dfa)  # 副本

            for dfa in all_DFA:
                if dfa in visited_dfa:  # 已经访问过，则continue
                    continue
                visited_dfa.append(dfa)  # 加入close表
                item = dfa.pros_
                for v in V:
                    new_item = self.go(item, v)
                    if new_item is not None:
                        new_dfa = DFA(-1, new_item, {})
                        idx = self.exist_idx(all_DFA, new_dfa)
                        if idx == -1:  # 不存在，添加新dfa
                            new_dfa.id_ = len(all_DFA)
                            dfa.next_ids_[v] = new_dfa.id_
                            all_DFA.append(new_dfa)
                        else:  # 存在，指向原有dfa
                            dfa.next_ids_[v] = idx

            if len(old_visted_dfa) == len(visited_dfa):  # close表长度不变，退出循环
                break

        return all_DFA

    def print_DFA(self, all_DFA):
        for dfa in all_DFA:
            print("====")
            print(f"id={dfa.id_}")
            print(f"item={dfa.pros_}")
            print(f"next={dfa.next_ids_} \n")

    def step4_draw_DFA(self, all_DFA):
        # 创建Digraph对象
        dot = graphviz.Digraph(comment='SLR1_DFA', graph_attr={'rankdir': 'LR'})
        for dfa in all_DFA:
            label = f"I{dfa.id_}\n"
            node_color = "lightblue"
            if dfa.id_ == 0:
                node_color = "lightpink"
            for pro in dfa.pros_:
                label += pro + "\n"
            dot.node(str(dfa.id_), label=label,
                     style='filled', fillcolor=node_color,
                     shape='rectangle', fontname='Verdana')

            if len(dfa.next_ids_) != 0:
                for v, to_id in dfa.next_ids_.items():
                    dot.edge(str(dfa.id_), str(to_id), label=v, fontcolor='red')
        # 显示图形
        # dot.view()
        return dot.source

    def step5_check_SLR1(self, all_DFA):  # 判断是否为SLR1文法
        flag = True
        for dfa in all_DFA:
            item = dfa.pros_
            shift_num = 0  # 移进数目
            protocol_num = 0  # 归约数目
            shift_vt = set()
            protocol_vn = set()
            shift_pro = set()
            protocol_pro = set()
            for pro in item:
                dot_left, dot_right = pro.split(".")
                if dot_right == "":  # .在最后，为归约项目
                    # if dot_left[:2] == self.S + "'":  # 接受项目，不考虑为归约项目
                    #     continue
                    protocol_num += 1
                    pro_left, pro_right = pro.split("->")
                    protocol_vn.add(pro_left)
                    protocol_pro.add(pro)
                elif dot_right[0] in self.Vt:  # .后面为终结符，为移进项目；
                    shift_num += 1
                    shift_vt.add(dot_right[0])
                    shift_pro.add(pro)
            if protocol_num == 1 and shift_num >= 1:  # SLR能解决 移进归约冲突（只存在一个归约）
                shift_conf_msg = ""
                for s_pro in shift_pro:
                    shift_conf_msg += s_pro + " "
                print(f"I{dfa.id_}中：{shift_conf_msg} 与  {next(iter(protocol_pro))}存在移进-归约冲突")
                for vt in shift_vt:
                    for vn in protocol_vn:
                        if self.first[vt].intersection(self.follow[vn]):  # 有交集
                            flag = False
                            print(f"它们的first与follow交集不为空，不满足SLR")
                            return flag
                flag = True
                print(f"但它们的first与follow交集为空，可忽略")
            elif protocol_num >= 2:  # SLR不能解决 归约-归约冲突
                pro_conf_msg = ""
                for p_pro in protocol_pro:
                    pro_conf_msg += p_pro + " "
                print(f"I{dfa.id_}中: {pro_conf_msg} 存在归约-归约冲突，不满足SLR")
                flag = False

        return flag

    def step6_construct_SLR1_table(self, all_DFA, formulas_list):
        actions = {}
        gotos = {}
        for dfa in all_DFA:
            id_ = dfa.id_
            next_ids = dfa.next_ids_
            if len(next_ids) == 0:  # 无下一个状态，必定为归约项目或接受项目，且只有一个产生式
                pro = dfa.pros_[0].replace(".", "")  # 去除.
                if pro == formulas_list[0]:  # 如果这一个为接受项目：S'->S
                    actions[(id_, "#")] = "acc"
                else:  # 其他的指定产生式
                    # ===========LR0===========
                    # for vt in self.Vt:
                    #     actions[(id_, vt)] = "r" + str(formulas_list.index(pro))
                    # actions[(id_, "#")] = "r" + str(formulas_list.index(pro))

                    # ===========SLR1===========
                    pro_left, pro_right = pro.split("->")
                    for ch in self.follow[pro_left]:
                        actions[(id_, ch)] = "r" + str(formulas_list.index(pro))
                    actions[(id_, "#")] = "r" + str(formulas_list.index(pro))
            else:  # 有指向下一个项目，同时当前项目可能存在接受项目、归约项目（点在末尾）、移进项目
                for item in dfa.pros_:
                    pro_left, pro_right = item.split(".")
                    if pro_right == "":  # .在最后   为归约项目
                        pro = item.replace(".", "")
                        if pro == formulas_list[0]:  # 为接受项目
                            actions[(id_, "#")] = "acc"
                        else:  # 为其他的归约项目
                            left, right = pro.split("->")
                            if right == '':  # 由于在生成all_dot_pro时把A->ε ==> A->.，因此这里需要复原判断一下
                                pro += 'ε'
                            for ch in self.follow[left]:
                                actions[(id_, ch)] = "r" + str(formulas_list.index(pro))
                            actions[(id_, "#")] = "r" + str(formulas_list.index(pro))

                for v, to_dfa_id in next_ids.items():
                    if v in self.Vt:
                        actions[(id_, v)] = "s" + str(to_dfa_id)
                    elif v in self.Vn:
                        gotos[(id_, v)] = to_dfa_id

        # 转成df对象
        merged_dict = {key: value for d in (actions, gotos) for key, value in d.items()}
        sorted_keys = sorted(merged_dict.keys(), key=lambda x:
        (x[1].isupper(), x[1] == "#", x[1]))
        sort_dict = {key: merged_dict[key] for key in sorted_keys}
        columns = []
        for k in sort_dict.keys():
            if k[1] not in columns:
                columns.append(k[1])
        rows = set(key[0] for key in sort_dict.keys())
        df = pd.DataFrame(index=rows, columns=columns)
        for key, value in sort_dict.items():
            df.loc[key[0], key[1]] = value

        # print(df)
        return actions, gotos

    def step7_SLR1_analyse(self, actions, gotos, formulas_list, input_str):
        s = list(input_str)
        s.append("#")
        sp = 0  # 字符串指针

        state_stack = []
        symbol_stack = []
        state_stack.append(0)
        symbol_stack.append("#")

        step = 0
        msg = ""
        info_step, info_state_stack, info_symbol_stack, info_str, info_msg, info_res = [], [], [], [], [], ""
        # 分析
        while sp != len(s):
            step += 1
            ch = s[sp]
            top_state = state_stack[-1]
            top_symbol = symbol_stack[-1]
            info_step.append(step)
            info_state_stack.append("".join([str(x) for x in state_stack]))
            info_symbol_stack.append("".join(symbol_stack))
            info_str.append("".join(s[sp:]))
            if (top_state, ch) not in actions.keys():
                info_res = f"error：分析失败，找不到Action({(top_state, ch)})"
                info_msg.append("error")
                break
            find_action = actions[(top_state, ch)]

            if find_action[0] == "s":  # 移进操作
                state_stack.append(int(find_action[1:]))
                symbol_stack.append(ch)
                sp += 1
                msg = f"Action[{top_state},{ch}]={find_action}: 状态{find_action[1:]}入栈"
            elif find_action[0] == 'r':  # 归约操作
                pro = formulas_list[int(find_action[1:])]  # 获取第r行的产生式
                pro_left, pro_right = pro.split("->")
                pro_right_num = len(pro_right) if pro_right != 'ε' else 0
                for i in range(pro_right_num):
                    state_stack.pop()
                    symbol_stack.pop()
                symbol_stack.append(pro_left)
                goto_key = (state_stack[-1], symbol_stack[-1])
                if goto_key in gotos.keys():
                    msg = f"Action[{top_state},{ch}]={find_action}: 用{pro}归约，Goto[{state_stack[-1]},{symbol_stack[-1]}]={gotos[goto_key]}入栈"
                    state_stack.append(gotos[goto_key])
                else:
                    info_res = f"error：分析失败，找不到GOTO({state_stack[-1]},{symbol_stack[-1]})"
            elif find_action == "acc":
                msg = "acc: 分析成功！"
                info_msg.append(msg)
                info_res = "Success!"
                break
            info_msg.append(msg)

        # print
        # for i in range(len(info_step)):
        #     print(f"{info_step[i]}\t{info_state_stack[i]}\t{info_symbol_stack[i]}\t{info_str[i]}\t{info_msg[i]}\n")

        info = {
            "info_step": info_step,
            "info_state_stack": info_state_stack,
            "info_symbol_stack": info_symbol_stack,
            "info_str": info_str,
            "info_msg": info_msg,
            "info_res": info_res
        }
        return info

    def init(self):
        self.S, self.Vn, self.Vt, self.formulas_list, self.first, self.follow = self.step1_pre_process(
            self.formulas_list)
        self.dot_items = self.step2_all_dot_pros(self.formulas_list)  # 计算所有项目（带点）
        self.all_DFA = self.step3_construct_SLR1_DFA(self.dot_items)  # 计算项目集的DFA转换关系
        # self.print_DFA(self.all_DFA)
        self.dot = self.step4_draw_DFA(self.all_DFA)  # 画项目集的DFA转换图
        self.isSLR1 = self.step5_check_SLR1(self.all_DFA)
        if self.isSLR1:  # 检测是否符合SLR1文法
            self.actions, self.gotos = self.step6_construct_SLR1_table(self.all_DFA, self.formulas_list)  # 画表

    def solve(self, input_str):
        self.info = self.step7_SLR1_analyse(self.actions, self.gotos, self.formulas_list, input_str)


if __name__ == "__main__":
    grammar2 = [  # ppt上
        "S->BB",
        "B->aB",
        "B->b"
    ]
    grammar3 = [  # 直接左递归， 移进归约冲突  + *
        "E->E+T",
        "E->T",
        "T->T*F",
        "T->F",
        "F->(E)",
        "F->i"
    ]
    grammar5 = [  # 公共因子
        "E->b|bA",
        "A->c"
    ]
    grammar6 = [  # 间接左递归
        "S->Qc|c",
        "Q->Rb|b",
        "R->Sa|a"
    ]
    grammar7 = [  # 含ε
        "S->abcA",
        "A->d|ε"
    ]
    grammar8 = [  # 课后3.25习题
        'T->EbH',
        'E->d',
        'E->ε',
        'H->i',
        'H->Hbi',
        'H->ε'
    ]
    grammar9 = [
        'S->bAS',
        'S->bA',
        'A->aSc'
    ]
    slr1 = SLR1(grammar9)
    slr1.init()
    # slr1.solve("b")
    # slr1.solve("a+a")
    # slr1.solve("i+i")
    # slr1.solve("abc") # 7
