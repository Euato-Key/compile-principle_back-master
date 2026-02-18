import copy
from collections import defaultdict
import graphviz
import pandas as pd


class DFA:
    def __init__(self, id_, pros_, next_ids_):
        self.id_ = id_  # 编号
        self.pros_ = pros_  # productions
        self.next_ids_ = next_ids_  # { v1:id1 , v2:id2 ...}

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

    def eliminate_direct_left_recursion(self, grammar, non_terminal):
        productions = grammar[non_terminal]
        recursive_productions = []
        alphabet_list = [chr(i) for i in range(ord('A'), ord('Z') + 1)]  # A-Z，用于给新非终结符命名
        for production in productions:  # 找到含有左递归的候选式
            if production.startswith(non_terminal):
                recursive_productions.append(production)

        if len(recursive_productions) > 0:
            # 命名为A-Z且不与原有存在的非终结符重名
            for ch in alphabet_list:
                if ch not in grammar.keys():
                    new_non_terminal = ch
                    break

            # S = Sab \ Scd \ T \ F
            # 更新原始非终结符的产生式  S = (T\F) S'
            grammar[non_terminal] = [p + new_non_terminal for p in productions if not p.startswith(non_terminal)]

            # 添加新的非终结符的产生式  S'=(ab\cd) S'
            grammar[new_non_terminal] = [p[1:] + new_non_terminal for p in recursive_productions if
                                         p.startswith(non_terminal)]
            grammar[new_non_terminal].append('ε')  # S'=(ab\cd)S' \ ε

        return grammar

    def is_recruse(self, grammar, non_terminals, iidx, cur, pre):  # 往后预测，看是否会出现间接左递归

        check = False
        set_front_con = set()  # pre右侧所有可能递归的vn
        for pre_production in grammar[pre]:
            if pre_production[0].isupper():
                set_front_con.add(pre_production[0])

        set_back_con = set()
        for i in range(iidx, len(non_terminals)):  # 遍历所有非终结符 curback = cur......最后一个终结符
            cur_back = non_terminals[i]
            if i == len(non_terminals) - 1:  # 若为最后一个终结符，则加入自身
                set_back_con.add(cur_back)
            for cur_back_pro in grammar[cur_back]:  # 遍历当前cur_back的候选式
                if cur_back_pro.startswith(cur):
                    set_back_con.add(cur_back)

        if len(set_front_con & set_back_con) != 0:  # 有交集
            check = True

        return check

    def eliminate_left_recursion(self, grammar):
        non_terminals = list(grammar.keys())[::-1]  # 逆序，将开始符放到最后
        replaced_vn = []  # 记录被替换代入掉的非终结符
        for i in range(len(non_terminals)):  # 遍历所有非终结符
            cur = non_terminals[i]
            # 间接左递归--》直接左递归
            for j in range(i):  # 遍历 pre1,pre2,pre3.....cur的非终结符（cur前面的终结符）
                pre = non_terminals[j]
                new_productions = set()
                for cur_production in grammar[cur]:
                    if cur_production.startswith(pre):  # 在cur的所有候选式中，找到以pre开头的候选式
                        if self.is_recruse(grammar, non_terminals, i, cur, pre):  # 若最终能产生间接左递归，进行代入合并处理
                            rest_str = cur_production.replace(pre, '', 1)  # 截取cur的该候选式去除首字符后的剩余字符
                            replaced_vn.append(pre)

                            for pre_production in grammar[pre]:  # 加入到pre的所有候选式后面
                                new_productions.add(pre_production + rest_str)
                        else:  # 不进行代入合并处理
                            new_productions.add(cur_production)
                    else:
                        new_productions.add(cur_production)
                grammar[cur] = new_productions
            grammar = self.eliminate_direct_left_recursion(grammar, cur)  # 消除当前的直接左递归

        # 消除冗余产生式（那些被替换代入的产生式）
        for vn in replaced_vn:
            del grammar[vn]

        return grammar

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
        # 消除左递归
        formulas_dict = self.eliminate_left_recursion(formulas_dict)

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
                        if next_symbol == v:
                            break
                        self.cal_v_first(next_symbol)
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

    def cal_all_first(self):
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
                            # self.follow[vn].add('#')
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
        # print("=============FirstFollow=============")
        self.formulas_dict, self.S, self.Vn, self.Vt = self.process(self.formulas_list)
        self.cal_all_first()
        self.cal_all_follow()
        # print(f"first: {self.first}")
        # print(f"follow: {self.follow}")
        # print("=============FirstFollow=============")

        return self.first, self.follow


class LR0:
    def __init__(self, formulas_list):
        self.formulas_list = formulas_list
        self.S = ""
        self.Vn = []
        self.Vt = []
        self.dot_items = []  # 所有可能的.项目集
        self.dot = ""
        self.all_DFA = []
        self.actions = {}
        self.gotos = {}
        self.info = {}
        self.isLR0 = False

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

        return S, Vn, Vt, formulas_list

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

    def step3_construct_LR0_DFA(self, dot_items):
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
            print("====================")
            print(f"id={dfa.id_}")
            print(f"item={dfa.pros_}")
            print(f"next={dfa.next_ids_} \n")

    def step4_draw_DFA(self, all_DFA):
        # 创建Digraph对象
        dot = graphviz.Digraph(comment='LR0_DFA', graph_attr={'rankdir': 'LR'})
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
        # print(dot.source)
        # print(type(dot.source))
        return dot.source

    def step5_check_LR0(self, all_DFA):  # 判断是否为LR0文法
        flag = True
        for dfa in all_DFA:
            item = dfa.pros_
            shift_num = 0  # 移进数目
            protocol_num = 0  # 归约数目
            for pro in item:
                dot_left, dot_right = pro.split(".")
                if dot_right == "":  # .在最后，为归约项目
                    # if dot_left[:2] == self.S + "'":  # 接受项目，不考虑为归约项目
                    #     continue
                    protocol_num += 1
                elif dot_right[0] in self.Vt:  # .后面为终结符，为移进项目
                    shift_num += 1
            if (protocol_num >= 1 and shift_num >= 1) or protocol_num >= 2:
                conflict = "归约-归约冲突" if protocol_num >= 2 else "移进-归约冲突"
                print(f"I{dfa.id_}存在{conflict}")
                flag = False

        return flag

    def step6_construct_LR0_table(self, all_DFA, formulas_list):
        actions = {}
        gotos = {}
        for dfa in all_DFA:
            id_ = dfa.id_
            next_ids = dfa.next_ids_
            if len(next_ids) == 0:  # 无下一个状态，必定为归约项目或接受项目，且只有一个
                pro = dfa.pros_[0].replace(".", "")  # 去除.
                if pro == formulas_list[0]:  # 如果这一个为接受项目：S'->S
                    actions[(id_, "#")] = "acc"
                else:  # 其他的指定产生式
                    # ===========LR0===========
                    for vt in self.Vt:
                        actions[(id_, vt)] = "r" + str(formulas_list.index(pro))
                    actions[(id_, "#")] = "r" + str(formulas_list.index(pro))

                    # ===========SLR1===========
                    # pro_left, pro_right = pro.split("->")
                    # for ch in self.follow[pro_left]:
                    #     actions[(id_, ch)] = "r" + str(formulas_list.index(pro))
                    # actions[(id_, "#")] = "r" + str(formulas_list.index(pro))
            else:  # 有指向下一个项目，同时当前项目可能存在接受项目
                for item in dfa.pros_:
                    pro_left, pro_right = item.split(".")
                    if pro_right == "":  # .在最后 为归约项目
                        pro = item.replace(".", "")
                        if pro == formulas_list[0]:  # 为接受项目
                            actions[(id_, "#")] = "acc"
                            break

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
        # df = pd.DataFrame(index=rows, columns=columns)
        # for key, value in sort_dict.items():
        #     df.loc[key[0], key[1]] = value
        #
        # print(df)
        return actions, gotos

    def step7_LR0_analyse(self, actions, gotos, formulas_list, input_str):
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
        self.S, self.Vn, self.Vt, self.formulas_list = self.step1_pre_process(self.formulas_list)
        self.dot_items = self.step2_all_dot_pros(self.formulas_list)  # 计算所有项目（带点）
        self.all_DFA = self.step3_construct_LR0_DFA(self.dot_items)  # 计算项目集的DFA转换关系
        self.print_DFA(self.all_DFA)
        self.dot = self.step4_draw_DFA(self.all_DFA) # 画项目集的DFA转换图
        self.isLR0 = self.step5_check_LR0(self.all_DFA)
        if self.isLR0:  # 检测是否符合SLR1文法
            self.actions, self.gotos = self.step6_construct_LR0_table(self.all_DFA, self.formulas_list)  # 画表

    def solve(self, input_str):
        self.info = self.step7_LR0_analyse(self.actions, self.gotos, self.formulas_list, input_str)


if __name__ == "__main__":
    # 注意使用无空格的测试用例（前端处理空白）
    grammar1 = [  # ＋
        "E->E+T|T",
        "T->(E)|a",
    ]
    grammar2 = [  # ppt上·
        "S->BB",
        "B->aB",
        "B->b"
    ]
    grammar3 = [  # web
        "E->aA",
        "E->bB",
        "A->cA",
        "A->d",
        "B->cB",
        "B->d"
    ]
    grammar4 = [  # + * :移进归约冲突
        "E->E+T",
        "E->T",
        "T->T*F",
        "T->F",
        "F->(E)",
        "F->i"
    ]
    grammar5 = [  # 公共因子 移进归约冲突
        "E->b|bA",
        "A->c"
    ]
    grammar6 = [  # 间接左递归、移进归约冲突
        "S->Qc|c",
        "Q->Rb|b",
        "R->Sa|a"
    ]
    grammar7 = [  # 含ε， 移进归约冲突
        "S->abcA|bcA|cA",
        "A->abcA|ε"
    ]
    grammar7 = [  # 含ε， 移进归约冲突
        "A->a|c|d|c|e|f|g|h|i|j|k|m"
    ]
    grammar10 = [
        'S->Aa',
        'A->BD',
        'B->b',
        'D->d'
    ]

    lr0 = LR0(grammar10)
    lr0.init()
    print(lr0.f)
    # lr0.analyse_str("a+a+(a+a)") # 1
    # lr0.analyse_str("bc") # 5
    lr0.solve("bcabc")  # 6/7
