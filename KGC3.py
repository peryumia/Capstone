# MATCH (n)-[r]->(m) RETURN n,r,m

"""
构建调度知识图谱
只分main constraint和additional constraint，保留具体公式
"""

from pathlib import Path
import json
from py2neo import Graph

# ───────────── 1. Neo4j 连接配置 ─────────────
NEO4J_URI      = "bolt://localhost:7681"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "capstone"
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
graph.delete_all()

# ───────────── 2. 定义节点标签并建唯一约束 ─────────────
labels = [
    "Problem", "ProblemType", "Objective",
    "MainConstraint", "AdditionalConstraint",  # 简化为两类约束
    "Parameter", "DecisionVariable",
]
for lbl in labels:
    graph.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{lbl}) REQUIRE n.name IS UNIQUE")

# ───────────── 3. 读取 JSON 文件 ─────────────
BASE_DIR = Path.cwd()
FILES = [
    "flow shop2/Basic hybrid flow shop scheduling problem/basic_settings_with_std.json",
    "flow shop2/distributed hybrid flow shop scheduling problem with assembly/distributed hybrid flow shop scheduling problem with assembly_with_std.json",
    "flow shop2/distributed hybrid flow shop scheduling problem with the blocking Constraints/distributed hybrid flow shop scheduling problem with the blocking Constraints_with_std.json",
    "flow shop2/distributed hybrid flow shop scheduling problem with the job merging/distributed hybrid flow shop scheduling problem with the job merging_with_std.json",
    "flow shop2/Distributed lot-streaming scheduling problem with hybrid flow shop/lot-streaming scheduling_with_std.json",
    "flow shop2/Flexible flow shop problem with arrive and due time/Flexible flow shop problem with arrive and due time_new_with_std.json",
    "flow shop2/Flexible flow shop scheduling minimizing the energy consumption and the total weighted tardiness/Flexible flow shop scheduling minimizing the energy consumption and the total weighted tardiness_with_std.json",
    "flow shop2/Flexible flow shop scheduling problem with blocking constraint/Flexible flow shop scheduling problem with blocking constraint_with_std.json",
    "flow shop2/hybrid flow shop scheduling problem with limited human resource/hybrid flow shop scheduling problem with limited human resource_with_std.json",
    "flow shop2/Hybrid flow shop scheduling problem with minimal maximal tradiness or makespan/Solving the hybrid flow shop scheduling problem to minimize the maximal tardiness or the maximal makespan of all jobs_with_std.json",
    "flow shop2/Minimising makespan in job shop scheduling problem with mobile robots/Minimising makespan in job shop scheduling problem with mobile robots_with_std.json",
    "flow shop2/Minimizing makespan for solving the distributed no-wait flowshop scheduling problem/Minimizing makespan for solving the distributed no-wait flowshop scheduling problem_with_std.json",
    "flow shop2/Multi-objective scheduling in hybrid flow shop with unrelated machines, machine eligibility and sequence-dependent setup times (SDST)/Multi-objective scheduling in hybrid flow shop with unrelated machines, machine eligibility and sequence-dependent setup times (SDST)_with_std.json",
    "flow shop2/Solving the hybrid flow shop scheduling problem with limited human resource constraint/Solving the hybrid flow shop scheduling problem with limited human resource constraint_with_std.json",
    "flow shop2/Solving the hybrid flow shop scheduling problem with the Sequence-dependent setup times/Solving the hybrid flow shop scheduling problem with the Sequence-dependent setup times_with_std.json",
    "flow shop2/Solving the Hybrid FlowShop Problems with batch production at the last stage/Solving the Hybrid FlowShop Problems with batch production at the last stage_with_std.json",

    "Job Shop/A hybrid artificial bee colony algorithm for flexible job shop scheduling with worker flexibility_with_std.json",
    "Job Shop/Ageing workforce effects in Dual-Resource Constrained job-shop scheduling_with_std.json",
    "Job Shop/FJSP considering emitted carbon footprint and late work criteria_with_std.json",
    "Job Shop/Flexible JSP with buffer_with_std.json",
    "Job Shop/Flexible JSP_with_std.json",
    "Job Shop/Job Shop Scheduling considering job weight, job arrival and due time, and job priority_with_std.json",
    "Job Shop/Job Shop Scheduling considering job weight, job arrival and due time, and machine maintenance windows_with_std.json",
    "Job Shop/job shop scheduling problem with human operators in handicraft production_with_std.json",
    "Job Shop/Job shop scheduling with the option of jobs outsourcing_with_std.json",
    "Job Shop/Job Shop Scheduling without sequential operation constraint_with_std.json",
    "Job Shop/JSP considering material handling_with_std.json",
    "Job Shop/JSP-dual resource constrained (machine and worker)_with_std.json",
    "Job Shop/MILP models for energy-aware flexible job shop scheduling problem_with_std.json",
    "Job Shop/Minimizing makespan in no-wait Job Shop scheduling problem_with_std.json",

    "Distributed Job Shop2/A memetic algorithm for multi-objective flexible job-shop problem with worker flexibility_with_std.json",
    "Distributed Job Shop2/A modified genetic algorithm approach for scheduling of perfect maintenance in distributed production scheduling_with_std.json",
    "Distributed Job Shop2/An Effective Multi-Objective Artificial Bee Colony Algorithm forEnergy Efficient Distributed Job Shop Scheduling_with_std.json",
    "Distributed Job Shop2/DFSP-no idle time_with_std.json",
    "Distributed Job Shop2/DFSP-operation inspection_with_std.json",
    "Distributed Job Shop2/DFSP-single assembly_with_std.json",
    "Distributed Job Shop2/Distributed Flexible Job-Shop Scheduling Problem Based on Hybrid Chemical Reaction Optimization Algorithm_with_std.json",
    "Distributed Job Shop2/Distributed Job Shop Scheduling considering Transportation Time and without Sequential Operation Constraint_with_std.json",
    "Distributed Job Shop2/Distributed Job Shop Scheduling considering transportation time, factory maintenance windows, and job precedence_with_std.json",
    "Distributed Job Shop2/Distributed Job Shop Scheduling considering transportation time, factory maintenance windows, and without Sequential Operation Constraint_with_std.json",
    "Distributed Job Shop2/Distributed scheduling_with_std.json",
    "Distributed Job Shop2/Distributed with distance costs_with_std.json",
    "Distributed Job Shop2/Distributed with worker allocation_with_std.json",
    "Distributed Job Shop2/Solving distributed and flexible job-shop scheduling problems for a real-world fastener manufacturer_with_std.json",
    "Distributed Job Shop2/The distributed no-idle permutation flowshop scheduling problem with due windows_with_std.json"
]

data_list = [json.loads((BASE_DIR / p).read_text(encoding="utf-8")) for p in FILES]

# ───────────── 4. 组织节点与关系 ─────────────
nodes = {lbl: {} for lbl in labels}
rels  = []

global_constraint_counter = 0
for d in data_list:
    # ---- Problem ----
    prob_title = d.get("title", "UNKNOWN_TITLE")
    prob_desc = (d.get("description") or "").strip()
    nodes["Problem"][prob_title] = {"name": prob_title, "description": prob_desc}

    # ProblemType
    prob_type = d.get("type", "UNKNOWN_TYPE")
    nodes["ProblemType"][prob_type] = {"name": prob_type}

    # Problem → ProblemType
    rels.append(("Problem", prob_title, "HAS_TYPE", "ProblemType", prob_type, {}))

    # ---- Parameters & Decision Variables ----
    param_sym2name, dv_sym2name = {}, {}   # 映射到“最终节点名”（含重名加序号后）
    for p in d["Nomenclature"]["Parameters"]:
        base = p["std_name"]                               # 用 std_name 作为基础名
        name = base
        idx = 2                                            # 重名追加序号，从 2 开始
        while name in nodes["Parameter"]:
            name = f"{base} {idx}"
            idx += 1
        nodes["Parameter"][name] = {                       # 保留 symbol / definition
            "name": name,
            "symbol": p.get("symbol", ""),
            "definition": p.get("definition", "")
        }
        # 符号到最终节点名（支持逗号分隔）
        sym_raw = (p.get("symbol") or "").strip()
        if sym_raw:
            for s in [x.strip() for x in sym_raw.split(",") if x.strip()]:
                param_sym2name[s] = name

    for dv in d["Nomenclature"]["Decision Variables"]:
        base = dv["std_name"]                              # 用 std_name 作为基础名
        name = base
        idx = 2
        while name in nodes["DecisionVariable"]:
            name = f"{base} {idx}"
            idx += 1
        nodes["DecisionVariable"][name] = {                # 保留 symbol / definition / type
            "name": name,
            "symbol": dv.get("symbol", ""),
            "definition": dv.get("definition", ""),
            "type": dv.get("type", "")
        }
        sym_raw = (dv.get("symbol") or "").strip()
        if sym_raw:
            for s in [x.strip() for x in sym_raw.split(",") if x.strip()]:
                dv_sym2name[s] = name

    # ===== Objective Function =====
    obj = d["Formulation"]["Objective Function"]
    base_obj = obj["std_name"]                             # 用 std_name 作为基础名
    obj_key = base_obj
    idx = 2
    while obj_key in nodes["Objective"]:
        obj_key = f"{base_obj} {idx}"
        idx += 1
    nodes["Objective"][obj_key] = {                        # 保留 description 和 function
        "name": obj_key,
        "description": obj.get("description", ""),
        "function": obj.get("function", "")
    }
    rels.append(("Problem", prob_title, "HAS_OBJECTIVE", "Objective", obj_key, {}))

    # 读取混合列表（可能混写参数/变量符号）
    rv = obj.get("related Decision Variables", [])
    if isinstance(rv, str):
        rv = [rv]

    for sym in rv:
        s = sym.strip()
        if s in dv_sym2name:
            rels.append(("Objective", obj_key, "HAS_DECISION_VARIABLE", "DecisionVariable", dv_sym2name[s], {}))
        elif s in param_sym2name:
            rels.append(("Objective", obj_key, "HAS_PARAMETER", "Parameter", param_sym2name[s], {}))
        else:
            print(f"[WARN] 未识别符号 '{s}' (Objective {obj_key})")

    # ===== Constraints：简化为两类，保留具体公式 =====
    # 这里开始是本次“新增/修改”的主要位置
    for c in d["Formulation"]["Constraints"]:
        # 确定约束类型
        constraint_type = c.get("type", "").strip().lower()
        if "main" in constraint_type:
            constraint_label = "MainConstraint"
        elif "additional" in constraint_type:
            constraint_label = "AdditionalConstraint"
        else:
            constraint_label = "AdditionalConstraint"
        
        # 基本字段
        constraint_function    = c.get("function", "")                   # 原有：函数表达式
        constraint_description = (c.get("description") or "").strip()    # CHANGED: 新增 description
        omt_super = (c.get("super") or c.get("super_type") or "").strip()    # CHANGED: 新增 OMT_* 三个属性
        omt_sub   = (c.get("sub")   or c.get("sub_type")   or "").strip()    # CHANGED
        omt_detail= (c.get("detail")or c.get("detail_type")or "").strip()    # CHANGED
        
        # 全局唯一命名：constraint 0, 1, 2, ...
        constraint_id = f"constraint {global_constraint_counter}"
        global_constraint_counter += 1
        
        # 约束节点属性：去掉 problem；新增 description 与 OMT_* 三个字段
        nodes[constraint_label][constraint_id] = {
            "name": constraint_id,
            "function": constraint_function,
            "description": constraint_description,          # CHANGED: 新增
            "OMT_super_type": omt_super,                   # CHANGED: 新增
            "OMT_sub_type": omt_sub,                       # CHANGED: 新增
            "OMT_detail_type": omt_detail                  # CHANGED: 新增
            # "problem": prob_title                        # CHANGED: 移除（不再写入）
        }
        
        # Problem → Constraint
        rels.append(("Problem", prob_title, "HAS_CONSTRAINT", constraint_label, constraint_id, {}))
        
        # Constraint 使用参数和决策变量（保持不变，仍按最终节点名连边）
        for param in c.get("related Parameters", []):
            key = (param or "").strip()
            name = param_sym2name.get(key) or nodes["Parameter"].get(key, {}).get("name")
            if name:
                rels.append((constraint_label, constraint_id, "USES_PARAMETER", "Parameter", name, {}))
        
        for dv in c.get("related Decision Variables", []):
            key = (dv or "").strip()
            name = dv_sym2name.get(key) or nodes["DecisionVariable"].get(key, {}).get("name")
            if name:
                rels.append((constraint_label, constraint_id, "USES_DECISION_VARIABLE", "DecisionVariable", name, {}))

# ───────────── 5. 写入 Neo4j ─────────────
tx = graph.begin()

def merge_node(label, key, props):
    tx.run(f"MERGE (n:{label} {{name:$key}}) SET n += $props", key=key, props=props)

def merge_rel(slabel, skey, rtype, elabel, ekey, props):
    tx.run(
        f"""
        MATCH (a:{slabel} {{name:$skey}})
        MATCH (b:{elabel} {{name:$ekey}})
        MERGE (a)-[r:{rtype}]->(b)
        SET   r += $props
        """, skey=skey, ekey=ekey, props=props
    )

for lbl, dic in nodes.items():
    for k, p in dic.items():
        merge_node(lbl, k, p)

for sl, sk, rt, el, ek, pr in rels:
    merge_rel(sl, sk, rt, el, ek, pr)

tx.commit()
print("Graph construction finished (simplified constraints with formulas)!")
