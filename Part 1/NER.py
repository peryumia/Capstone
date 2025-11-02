"""
在kg7.py基础上：
1. 尝试qwen3:14b
2. 每部分完成重启ollama防止同一窗口上下文爆炸
3. 允许ollama和vpn共存
"""

import sys, os, json
from pathlib import Path



import os

# 清除所有代理环境变量，防止请求走VPN代理
for key in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(key, None)

os.environ['no_proxy'] = 'localhost,127.0.0.1,127.0.0.1:11434'


import json
import re
from pathlib import Path, PurePath
import ollama


# -----------------------------------------------------------------------------
# 共用工具函数 -----------------------------------------------------------------
# -----------------------------------------------------------------------------
# ============== 轻量级 Ollama 封装 =========================
class OllamaClient:
    """一次性对话客户端：每次实例化相当于新开窗口。"""
    def __init__(self, model: str = "qwen3:14b"):
        self.model = model

    def ask(self, prompt: str) -> str:
        resp = ollama.chat(model=self.model,
                           messages=[{"role": "user", "content": prompt}])
        return resp["message"]["content"].strip().splitlines()[-1]

# ============== 共用工具 ==================================
def chat_last_line(prompt: str, client: OllamaClient) -> str:
    return client.ask(prompt)

# -----------------------------------------------------------------------------
# (1) 读取数据集 ------------------------------------------------------
# -----------------------------------------------------------------------------
json_files = [
    "flow shop/Basic hybrid flow shop scheduling problem/basic_settings_with_std.json",
    "flow shop/distributed hybrid flow shop scheduling problem with assembly/distributed hybrid flow shop scheduling problem with assembly_with_std.json",
    "flow shop/distributed hybrid flow shop scheduling problem with the blocking Constraints/distributed hybrid flow shop scheduling problem with the blocking Constraints_with_std.json",
    "flow shop/distributed hybrid flow shop scheduling problem with the job merging/distributed hybrid flow shop scheduling problem with the job merging_with_std.json",
    "flow shop/Distributed lot-streaming scheduling problem with hybrid flow shop/lot-streaming scheduling_with_std.json",
    "flow shop/Flexible flow shop problem with arrive and due time/Flexible flow shop problem with arrive and due time_new_with_std.json",
    "flow shop/Flexible flow shop scheduling minimizing the energy consumption and the total weighted tardiness/Flexible flow shop scheduling minimizing the energy consumption and the total weighted tardiness_with_std.json",
    "flow shop/Flexible flow shop scheduling problem with blocking constraint/Flexible flow shop scheduling problem with blocking constraint_with_std.json",
    "flow shop/hybrid flow shop scheduling problem with limited human resource/hybrid flow shop scheduling problem with limited human resource_with_std.json",
    "flow shop/Hybrid flow shop scheduling problem with minimal maximal tradiness or makespan/Solving the hybrid flow shop scheduling problem to minimize the maximal tardiness or the maximal makespan of all jobs_with_std.json",
    "flow shop/Minimising makespan in job shop scheduling problem with mobile robots/Minimising makespan in job shop scheduling problem with mobile robots_with_std.json",
    "flow shop/Minimizing makespan for solving the distributed no-wait flowshop scheduling problem/Minimizing makespan for solving the distributed no-wait flowshop scheduling problem_with_std.json",
    "flow shop/Multi-objective scheduling in hybrid flow shop with unrelated machines, machine eligibility and sequence-dependent setup times (SDST)/Multi-objective scheduling in hybrid flow shop with unrelated machines, machine eligibility and sequence-dependent setup times (SDST)_with_std.json",
    "flow shop/Solving the hybrid flow shop scheduling problem with limited human resource constraint/Solving the hybrid flow shop scheduling problem with limited human resource constraint_with_std.json",
    "flow shop/Solving the hybrid flow shop scheduling problem with the Sequence-dependent setup times/Solving the hybrid flow shop scheduling problem with the Sequence-dependent setup times_with_std.json",
    "flow shop/Solving the Hybrid FlowShop Problems with batch production at the last stage/Solving the Hybrid FlowShop Problems with batch production at the last stage_with_std.json",

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
    "Job Shop/Minimizing makespan in no-wait Job Shop scheduling problem_with_std.json"


]

problems = []
for file_path in json_files:
    with open(file_path, "r", encoding="utf-8") as f:
        problems.append((json.load(f), file_path))

# -----------------------------------------------------------------------------
# (2) 约束分类树与映射表 --------------------------------------------------------
# -----------------------------------------------------------------------------
classification_tree_text = """\
以下是约束分类树供你参考：
约束分类树如下：
Demand Constraints (LHS ≥ RHS):
1. Demand-LowerBound-Constant 
   Ensures that the quantity or amount of resource meets a fixed minimum level.
   Example: At least 100 units must be produced.
2. Demand-LowerBound-Variable 
   Requires the quantity or amount to meet a minimum that depends on other decision variables.
   Example: Production must meet at least the amount demanded.
3. Demand-LowerBound-BigM 
   Uses a large constant (Big-M) to activate or deactivate constraints conditionally.
   Often combined with binary variables for logic-based constraints.
4. Demand-QualityMinBlend 
   Sets a lower bound on the quality of blended products made from raw materials.
   Example: Average purity of the mix must be above a threshold.
5. Demand-SetCover-n=1 
   Exactly one option must be selected among many (set covering).
   Example: Choose exactly one supplier.
6. Demand-SetCover-n≥1 
   At least n options must be selected among many (weighted set covering).
   Example: Choose at least 3 suppliers.

Resource Limitation Constraints (LHS ≤ RHS):
7. Resource-UpperBound-Constant
   Limits quantity or amount using a fixed upper bound.
   Example: No more than 500 units available.
8. Resource-UpperBound-Variable 
   Upper bound depends on other variables or parameters.
   Example: Can't exceed available capacity per period.
9. Resource-UpperBound-BigM 
   Applies an upper bound conditionally using Big-M logic.
   Example: If a machine is selected, then it can't exceed its capacity.
10. Resource-QualityMaxBlend 
    Upper bound on (or limitation of) a quality-related attribute when blending raw materials.
    Example: The impurity level of the blended product must be no more than 5%.
11. Resource-SetPack-n=1 
    Select at most one option (set packing).
    Example: Only one machine may operate per time slot. 
12. Resource-SetPack-n≤k 
    Select at most k options (weighted set packing).
    Example: Use up to 3 workers per shift.

Conservation Constraints (LHS = RHS):
13. Conservation-FlowBalance
    Ensures that inflow equals outflow at a node (mass/flow conservation).
    Example: Flow_in = Flow_out.
14. Conservation-InterPeriodBalance
    Balances flow or inventory between two consecutive periods.
    Example: Inventory_t = Inventory_t-1 + Production_t - Demand_t.
15. Conservation-QuantityAssignment
    Defines one variable exactly as a function of others (assignment equality).
    Example: CompletionTime_ij = StartTime_ij + ProcessingTime_ij.
16. Conservation-InitialCondition
    Sets initial conditions or starting quantities.
    Example: Inventory_0 = InitialInventory.
17. Conservation-SetPartitioning-n = 1
    Exactly one option must be chosen among many (classical set partitioning).
    Example: Each job is assigned to exactly one machine.
18. Conservation-SetPartitioning-n > 1
    Exactly n (or a weighted sum of n) items must be chosen; n > 1.
    Example: Select exactly three production lines to run.
19. Conservation-SetPartitioning-n = 0 (Disallow)
    All options are disallowed; total assignment quantity equals zero.
    Example: If a certain condition holds, processing quantity on every machine is forced to zero.
20. Conservation-QualityEquality
    Equates the quality (often a weighted average) of raw-material inputs with the output quality.
    Example: Product purity equals the weighted average purity of input streams.


LogicCondition Constraints (Logical relationships):
21. LogicCondition-EitherOr-2 Option
    Exactly one of two mutually exclusive alternatives must occur.
    Example: Either machine A or machine B is selected for the job, not both.
22. LogicCondition-EitherOr-MultiOption
    Exactly one option out of several (A, B, C …) must occur.
    Example: A job is processed on one and only one line among lines 1, 2, 3.
23. LogicCondition-IfThen-Forward Implication
    If one (or all) of set A happens, then one (or all) of set X must also happen.
    Example: If a batch starts in furnace A, then cooling station X must be activated.
24. LogicCondition-IfThen-Reverse Implication
    One (or all) of set A can occur only if one (or all) of set X occurs.
    Example: A job can enter the finishing area only if quality inspection X is completed.
25. LogicCondition-IfThen-Indicator
    A continuous quantity is forced to equal a specified value when a yes/no decision is yes; otherwise it is forced to zero.
    Example: y = 1 ⇒ z = Q; y = 0 ⇒ z = 0, where y is binary and z is the quantity being “switched”.

Domain Constraints (Variable domains & eligibility)
26. Domain-Binary
    Restricts a variable to take only binary values (0 or 1).
    Example: x_ij ∈ {0, 1} indicates whether operation j is assigned to machine i.
27. Domain-Continuous
    Restricts a variable to take any real value within a continuous range.
    Example: 0 ≤ y ≤ 100, where y is a production quantity.
28. Domain-Discrete
    Restricts a variable to take only values from a discrete set (non-continuous).
    Example: Batch size must be one of {50, 100, 150}.
29. Domain-FixedValue
    Forces a variable to take a fixed value (often zero or a predetermined constant).
    Example: If a machine is ineligible for an operation ⇒ x_ij = 0.
"""

category_map = {
    1: {"super_type": "Demand", "name": "LowerBound", "detail_type": "Constant"},
    2: {"super_type": "Demand", "name": "LowerBound", "detail_type": "Variable"},
    3: {"super_type": "Demand", "name": "LowerBound", "detail_type": "BigM"},
    4: {"super_type": "Demand", "name": "QualityMinBlend", "detail_type": ""},
    5: {"super_type": "Demand", "name": "SetCover", "detail_type": "n=1"},
    6: {"super_type": "Demand", "name": "SetCover", "detail_type": "n≥1"},
    7: {"super_type": "Resource", "name": "UpperBound", "detail_type": "Constant"},
    8: {"super_type": "Resource", "name": "UpperBound", "detail_type": "Variable"},
    9: {"super_type": "Resource", "name": "UpperBound", "detail_type": "BigM"},
    10: {"super_type": "Resource", "name": "QualityMaxBlend", "detail_type": ""},
    11: {"super_type": "Resource", "name": "SetPack", "detail_type": "n=1"},
    12: {"super_type": "Resource", "name": "SetPack", "detail_type": "n≤k"},
    13: {"super_type": "Conservation", "name": "FlowBalance", "detail_type": ""},
    14: {"super_type": "Conservation", "name": "InterPeriodBalance", "detail_type": ""},
    15: {"super_type": "Conservation", "name": "QuantityAssignment", "detail_type": ""},
    16: {"super_type": "Conservation", "name": "InitialCondition", "detail_type": ""},
    17: {"super_type": "Conservation", "name": "SetPartitioning", "detail_type": "n=1"},
    18: {"super_type": "Conservation", "name": "SetPartitioning", "detail_type": "n>1"},
    19: {"super_type": "Conservation", "name": "SetPartitioning", "detail_type": "n=0"},
    20: {"super_type": "Conservation", "name": "QualityEquality", "detail_type": ""},
    21: {"super_type": "LogicCondition", "name": "EitherOr", "detail_type": "2-Option"},
    22: {"super_type": "LogicCondition", "name": "EitherOr", "detail_type": "Multi-Option"},
    23: {"super_type": "LogicCondition", "name": "IfThen", "detail_type": "Forward Implication"},
    24: {"super_type": "LogicCondition", "name": "IfThen", "detail_type": "Reverse Implication"},
    25: {"super_type": "LogicCondition", "name": "IfThen", "detail_type": "Indicator"},
    26: {"super_type": "Domain", "name": "Binary", "detail_type": ""},
    27: {"super_type": "Domain", "name": "Continous", "detail_type": ""},
    28: {"super_type": "Domain", "name": "Discrete", "detail_type": ""},
    29: {"super_type": "Domain", "name": "FixedValue", "detail_type": ""},
}

# -----------------------------------------------------------------------------
# (3) 逐文件处理 ---------------------------------------------------------------
# -----------------------------------------------------------------------------
for problem_data, file_path in problems:
    print("\n================ 处理文件: {} ================".format(Path(file_path).name))

    params = problem_data["Nomenclature"].get("Parameters", [])
    decision_vars = problem_data["Nomenclature"].get("Decision Variables", [])
    constraints = problem_data["Formulation"].get("Constraints", [])
    objective = problem_data["Formulation"].get("Objective Function", {})



    # ---------------------- (3-1) 参数命名 ----------------------
    client = OllamaClient()
    for p in params:
        symbol = p["symbol"]
        definition = p.get("definition", "")
        # 汇总该参数在所有约束中的出现（公式 + 描述）
        usage_formula_and_desc = []
        for constr in constraints:
            if "related Parameters" in constr and symbol in constr["related Parameters"]:
                formulas = constr.get("function", [])
                if not isinstance(formulas, list):
                    formulas = [formulas]
                desc = constr.get("description", "")
                for f in formulas:
                    usage_formula_and_desc.append(f"{f} —— {desc}" if desc else f)

        prompt = (
            f"你是调度问题方面的专家，现在给定参数：符号 {symbol}，其具体描述: {definition}\n"
        )
        if usage_formula_and_desc:
            prompt += "该参数参与的公式及描述如下：\n" + "\n".join(usage_formula_and_desc) + "\n"
        prompt += (
            f"根据上述信息，请为该参数 {symbol} 生成规范的实体命名用于知识图谱节点。"
            "要求名称清晰且可泛化，可以在知识图谱中反复利用，先在之前的命名库中寻找是否有符合的命名，"
            "如果没有请进行新的命名。命名举例：JobSet、ProcessingTime等。输出格式：只返回一个命名，不要输出任何多余内容。"
        )

        std_name = chat_last_line(prompt, client)
        p["std_name"] = std_name
        print(f"参数 {symbol} → {std_name}")
    print("所有参数命名完成\n")

    # ---------------------- (3-2) 决策变量命名 ------------------
    client = OllamaClient()
    for v in decision_vars:
        symbol = v["symbol"]
        definition = v.get("definition", "")

        usage_descs = []
        for constr in constraints:
            if "related Decision Variables" in constr and symbol in constr["related Decision Variables"]:
                formulas = constr.get("function", [])
                if not isinstance(formulas, list):
                    formulas = [formulas]
                desc = constr.get("description", "")
                for f in formulas:
                    usage_descs.append(f"{f} —— {desc}" if desc else f)

        prompt = (
            f"你是调度问题方面的专家，现在给定决策变量：符号 {symbol}，其具体描述: {definition}\n"
        )
        if usage_descs:
            prompt += "该变量参与的公式及描述如下：\n" + "\n".join(usage_descs) + "\n"
        prompt += (
            f"根据上述信息，请为该决策变量 {symbol} 生成规范的实体命名用于知识图谱节点。"
            "要求名称清晰且可泛化，可以在知识图谱中反复利用，先在之前的命名库中寻找是否有符合的命名，"
            "如果没有请进行新的命名。命名举例：JobCompletionTime、JobPrecedenceIndicator、Makespan等。"
            "输出格式：只返回一个命名，不要输出任何多余内容。"
        )

        std_name = chat_last_line(prompt, client)
        v["std_name"] = std_name
        print(f"决策变量 {symbol} → {std_name}")
    print("所有决策变量命名完成\n")

    # ---------------------- (3-3) 约束三层分类 ------------------
    for idx, c in enumerate(constraints, 1):
        client = OllamaClient()
        desc = c.get("description", "").strip()
        if not desc:
            continue
        formulas = c.get("function", [])
        formula_text = " ; ".join(formulas) if formulas else ""
        prompt = (
            f"你是调度问题方面的专家，现在给定约束公式：{formula_text}\n，以及该约束的具体描述：{desc}\n"
            f"给定以下完整的约束分类树：{classification_tree_text}\n"
            "根据上述分类树，判断该约束属于哪个类别。输出格式：只输出类别数字编号，不要任何多余内容，例如：10，25等。"
        )
        # print(prompt)
        reply = chat_last_line(prompt, client)
        code = int(re.match(r"(\d+)", reply).group(1)) if re.match(r"(\d+)", reply) else None
        info = category_map.get(code, {"super_type": "Unknown", "name": "Unknown", "detail_type": ""})
        c["super_type"] = info["super_type"]
        c["sub_type"] = info["name"]
        c["detail_type"] = info["detail_type"]
        print(f"约束 {idx}: {formula_text} → {info['super_type']}/{info['name']}/{info['detail_type']} (#{code})")
    print("所有约束分类完成\n")

    # ---------------------- (3-4) 目标函数命名 ------------------
    client = OllamaClient()
    obj_desc = objective.get("description", "")
    obj_func = objective.get("function", "")
    involved = objective.get("related Decision Variables", [])
    prompt = (
        f"目标函数：{obj_func}\n描述：{obj_desc}\n决策变量：{', '.join(involved) if involved else ''}\n"
        "根据上述描述，请为该目标生成规范的名称，以 Minimize/Maximize开头，两个单词之间不要空格。"
        "要求名称清晰且可泛化，可以在知识图谱中反复利用，先在之前的命名库中寻找是否有符合的命名，"
        "如果没有请进行新的命名。命名举例：MinimizeMakespan, MinimizeConsumption, MinimizeTardiness等。最终只输出一个名字。"
    )
    obj_name = chat_last_line(prompt, client)
    objective["std_name"] = obj_name
    print(f"目标函数 → {obj_name}\n")
    print("所有目标函数命名完成\n")

    # ---------------------- (3-5) 保存带标准化信息的数据集 --------
    orig_path = Path(file_path)
    out_path = orig_path.with_name(orig_path.stem + '_with_std.json')
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(problem_data, f, ensure_ascii=False, indent=2)
    print(f"已生成 {out_path.name}")

    # # ---------------------- (3-5) 保存带标准化信息的数据集，但写进output这个文件夹 --------
    # orig_path = Path(file_path).resolve()
    # out_dir = orig_path.parent  # 先尝试写到输入JSON所在目录

    # # 若该目录不可写，回退到脚本同级 outputs 目录（自动创建）
    # if not os.access(out_dir, os.W_OK):
    #     out_dir = Path(__file__).resolve().parent / "outputs"
    #     out_dir.mkdir(parents=True, exist_ok=True)

    # out_path = out_dir / f"{orig_path.stem}_with_std.json"
    # with open(out_path, "w", encoding="utf-8") as f:
    #     json.dump(problem_data, f, ensure_ascii=False, indent=2)
    # print(f"已生成 {out_path}")

# ---------------------------------- 结束 -------------------------------------
print("\n全部文件处理完毕。")
