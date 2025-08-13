
## 项目简介
本项目是编译原理教学辅助平台的后端代码，旨在为编译原理课程的教学和学习提供支持，包含词法分析、语法分析等相关功能的实现。

## 目录结构说明
- `Class_LL1_GrammarAnalysis.py`：实现LL(1)语法分析功能的Python文件。
- `Class_LR0_GrammarAnalysis.py`：实现LR(0)语法分析功能的Python文件。
- `Class_SLR1_GrammarAnalysis.py`：实现SLR(1)语法分析功能的Python文件。
- `environment.yml`：项目环境配置文件。
- `Regex_to_DFAM.py`：实现FA功能（正则表达式到确定有限自动机转换）的Python文件。
- `sever.py`：后端服务相关的Python文件。

## environment.yml文件解释
`environment.yml`文件用于定义项目运行所需的环境配置，具体内容包括：
- **name**：定义环境名称，你可以在创建或激活环境时使用该名称。
- **channels**：指定从哪些渠道获取包，常见的如`defaults`（Anaconda官方渠道）等。
- **dependencies**：列出项目依赖的包，包括通过Conda安装的包以及通过`pip`安装的包。在`dependencies`下，会先列出Conda可管理的包及其版本信息，然后通过`- pip:`字段列出需要通过`pip`安装的包。

## 安装项目环境
### 前提条件
确保你已经安装了Anaconda或Miniconda。

### 安装步骤
1. **克隆仓库**
在终端中执行以下命令，将项目仓库克隆到本地：
```bash
git clone https://gitee.com/luo-haojia/compile-principle_back.git
```
2. **进入项目目录**
```bash
cd compilePrinciple_back
```
3. **创建并激活环境**
使用以下命令创建项目环境：
```bash
conda env create -f environment.yml
```
环境创建完成后，激活该环境：
- 在Windows系统下：
```bash
conda activate [environment.yml中定义的环境名称]
```
- 在Linux和macOS系统下：
```bash
source activate [environment.yml中定义的环境名称]
```


