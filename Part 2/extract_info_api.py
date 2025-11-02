"""
从 PDF 转出的 Markdown 中，调用 DeepSeek 的 API 生成回复.
"""

import os
import re
import json
import argparse
from typing import Any, Dict, List
from jsonschema import Draft7Validator
from pathlib import Path

# =============== 输入/输出路径 ===============
IN_MD   = Path.home() / "Documents/研究生/Capstone/Part2/Input/1.md"
OUT_DIR = Path.home() / "Documents/研究生/Capstone/Part2/output"
out_path = OUT_DIR / IN_MD.with_suffix(".txt").name
out_path.parent.mkdir(parents=True, exist_ok=True)
# ===============================================================

try:
    from openai import OpenAI  # pip install openai>=1.0.0
except ImportError as e:
    raise ImportError("需要安装 openai 库：pip install --upgrade openai") from e

# -----------------------
# 1) 轻量封装：一次性对话
# -----------------------
# 复用原有类名与方法签名，内部实现改为 DeepSeek API，尽量减少对下游调用的影响
class OllamaClient:
    """（已改造）通过 DeepSeek API 与大模型进行一次性对话；必要时可改 model。"""
    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        # Your DeepSeek API Key
        api_key = "API KEY"

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"  # DeepSeek 的 OpenAI 兼容基地址
        )

    def ask_json(self, prompt: str, temperature: float = 0) -> str:
        """
        让模型返回文本。
        如需强制 JSON，可启用 response_format={"type":"json_object"}，但为保持“只做必要修改”，此处不启用。
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            # 如果你希望强制 JSON，可取消下一行注释（但会改变原行为）
            # response_format={"type": "json_object"},
        )
        return (resp.choices[0].message.content or "").strip()

# -----------------------
# 2) 目标 JSON Schema
# -----------------------
JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["paper_title", "problem_description", "problem_type",
                 "parameters", "decision_variables", "objective", "constraints"],
    "properties": {}
}

# -----------------------
# 3) Few-shot
# -----------------------
FEW_SHOT_EXAMPLE = """
1. problem description: "The multi-factory model consists of F factories, which are geographically distributed in different locations. Each factory has H_f machines. Each machine can perform various operations with different operating lead times (T_{ijfh}). Each machine is subject to a maximum machine age \\overline{M}. The machine age is defined as the cumulated operating time. If the machine age reaches \\overline{M}, maintenance must be carried out immediately after the current operation finishes. After maintenance, the machine age is reset to 0. The maintenance time may vary depending on the machine age. In common practice, the relationship between the required maintenance time and the machine age is usually obtained empirically. The problem is to satisfy I jobs, where each job has N_i operations. The traveling time between factory f and job i is denoted by D_{if}. The objective of the problem is to minimize the makespan of the jobs. ";

2. parameters:[{"symbol": "f", "definition": "index for factory"},{"symbol": "i","definition": "index for job"}];

3. decision variables: [{"symbol": "chi_{if}", "definition": "determines the assignment of job i to factory f"},{"symbol": "delta_{ijfhk}", "definition": "determines the scheduling of an operation j of job i in time slot k on machine h in factory f"}];

4. objective function:{"function": "\\min\\, C_{\\max}", "description": "Minimize the makespan."};

5. constraints: [{"function": "S_{i,j} \\ge E_{i,(j-1)} \\quad \\forall i\\in I,\\; j = 2,\\dots, N_i", "description": "Enforces that each operation j of job i cannot start before the (j - 1)-th operation finishes."}, {"function": "E_{i,j} \\;-\\; S_{i,j} \\;=\\; \\sum_{f\\in F}\\bigl(\\chi_{i,f},T_{i,j,f}\\bigr)","description": "Defines the processing time of operation j for job i based on its assigned factory."}].
""".strip()

# -----------------------
# 4) Prompt构造
# -----------------------
SYSTEM_INSTRUCTION = (
    "You are an expert in operations research. "
    "Please extract from the given paper one concrete scheduling problem instance and output ALL its components, "
    "including: (1) the problem description, (2) parameters and decision variables with their specific symbols and definitions, "
    "(3) the objective function, and (4) constraints with explicit equations and textual descriptions. "
    "Strictly follow the example format as shown in the example. Carefully read the paper text to ensure that the extracted instance is complete "
    "and faithful to the source. Do not fabricate content.")

def make_prompt(markdown_text: str) -> str:
    return (
        "给定以下论文文本内容，文本内容中包含一个调度问题实例的信息：\n"
        f"{markdown_text[:200000]}\n\n"
        "请根据给定的文本信息，从中抽取出有用的信息，也就是一个调度问题实例的全部组件，具体包括：该问题本身描述（problem description），"
        "参数（parameter）和决策变量（decision variable）的具体符号和描述，目标函数（objective function）和约束（constraint）的具体公式和描述。\n"
        "输出示例如下（严格按此格式输出）:\n"
        f"{FEW_SHOT_EXAMPLE}\n\n"
        "请仔细阅读给定论文信息，确保抽取具体调度实例的全部信息，并严格按照上面的示例格式输出：\n"
        "注意：请仅输出上述示例的五个部分（1~5）及其字段，保持 LaTeX 表达式的正确性，不要添加额外说明文本。\n"
    )

# -----------------------
# 5) JSON 提取 & 校验
# -----------------------
def parse_json_from_text(text: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}\s*$", text, flags=re.S)
    payload = m.group(0) if m else text
    return json.loads(payload)

def validate(payload: Dict[str, Any]) -> List[str]:
    validator = Draft7Validator(JSON_SCHEMA)
    errs = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    return [f"[{'/'.join(str(x) for x in err.path) or '<root>'}] {err.message}" for err in errs]

# -----------------------
# 6) 主流程
# -----------------------
def run(md_path: str, out_path: str, model: str = "deepseek-chat") -> None:  # [修改] 默认模型名改为 deepseek-chat
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        md_text = f.read()

    client = OllamaClient(model=model)  # [修改] 仍复用同名类，但内部已改为 DeepSeek API
    prompt = make_prompt(md_text)
    print("\n===== PROMPT (BEGIN) =====")
    print(prompt)
    print("===== PROMPT (END) =====\n")

    raw = client.ask_json(prompt, temperature=0.5)
    print("\n===== MODEL RAW OUTPUT (BEGIN) =====")
    print(raw)
    # print("===== MODEL RAW OUTPUT (END) =====\n")
    # Path(out_path).with_suffix(".raw.txt").write_text(raw, encoding="utf-8")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(raw)
    print(f"✅ 已保存：{out_path}")
    # data = parse_json_from_text(raw)
    # errors = validate(data)
    # if errors:
    #     print("⚠️ JSON Schema 校验发现问题（已照常输出文件，建议根据提示修正）：")
    #     for e in errors:
    #         print(" -", e)

    # with open(out_path, "w", encoding="utf-8") as f:
    #     json.dump(data, f, ensure_ascii=False, indent=2)
    # print(f"✅ 已保存：{out_path}")

def main():
    _ = argparse.ArgumentParser(description="(fixed paths) Extract scheduling problem text using DeepSeek API (replacing local Ollama).")
    # 直接用固定路径运行
    if not IN_MD.exists():
        raise FileNotFoundError(f"未找到输入文件：{IN_MD}")
    run(str(IN_MD), str(out_path), model="deepseek-chat")  # 指定 deepseek-chat

if __name__ == "__main__":
    main()
