# Capstone
Part 1 + Part 2

先跑part2，再跑part1，最后得到带std的标准json文件即可，全部发给我我去构造成最终知识图谱。

## Part 1
### 用LLM对实体进行统一命名
ollama pull qwen3:14b，跑NER.py，记得修改输入文件路径，输出会是带std的标准json文件。

## Part 2
### 从md中用LLM抽取信息
md文件放Input文件夹下面，跑extract_info_api.py，记得填写deepseek的api key，输出是output文件夹下同名的txt。

得到txt之后跑convert_to_json.ipynb，暂时是ollama的ds，晚点jaq会改成api形式，目前自己改一下txt路径可以跑，转换成所需的json文件，跑完之后检查一下。
