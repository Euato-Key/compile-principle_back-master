## 项目简介
本项目是编译原理教学辅助平台的后端代码，旨在为编译原理课程的教学和学习提供支持，包含词法分析、语法分析等相关功能的实现。

## 目录结构说明
- `Class_LL1_GrammarAnalysis.py`：实现LL(1)语法分析功能的Python文件。
- `Class_LR0_GrammarAnalysis.py`：实现LR(0)语法分析功能的Python文件。
- `Class_SLR1_GrammarAnalysis.py`：实现SLR(1)语法分析功能的Python文件。
- `environment.yml`：项目环境配置文件。
- `Regex_to_DFAM.py`：实现FA功能（正则表达式到确定有限自动机转换）的Python文件。
- `server.py`：后端服务主入口文件。
- `start_server.py`：服务器启动脚本（支持多种运行模式）。
- `gunicorn.conf.py`：Gunicorn生产服务器配置文件。
- `requirements.txt`：Python依赖包列表。
- `database/`：数据库模块目录。
- `blueprints/`：Flask蓝图目录（API路由）。
- `services/`：业务逻辑服务目录。
- `utils/`：工具函数目录。

## 快速启动

### 方式1：开发模式（推荐开发时使用）
```bash
python server.py
```
或
```bash
python start_server.py dev
```
- 使用Flask内置服务器
- 支持代码热重载
- 并发能力：1-2人同时

### 方式2：生产模式（推荐部署时使用）
```bash
python start_server.py prod
```
- 使用Gunicorn + Gevent
- 8个Worker进程，异步处理
- 并发能力：40+人同时

### 方式3：简化生产模式
```bash
python start_server.py prod-simple
```
- 使用纯Gunicorn（同步Worker）
- 8个Worker进程
- 并发能力：8-16人同时

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
cd compile-principle_back
```
3. **创建并激活环境**
使用以下命令创建项目环境：
```bash
conda env create -f environment.yml
```
环境创建完成后，激活该环境：
- 在Windows系统下：
```bash
conda activate compiler
```
- 在Linux和macOS系统下：
```bash
source activate compiler
```
4. **安装额外依赖（生产环境需要）**
```bash
pip install -r requirements.txt
```

## API接口说明

### AI代理接口
- `POST /api/ai/chat` - AI聊天（非流式）
- `POST /api/ai/chat/stream` - AI聊天（流式）
- `GET /api/ai/balance` - 查询API余额
- `GET /api/ai/token-usage` - 查询Token使用统计
- `GET /api/ai/models` - 获取可用模型列表

### 统计数据接口
- `POST /api/stats/record` - 记录错误统计
- `GET /api/stats/summary` - 获取统计摘要
- `GET /api/stats/export` - 导出数据
- `POST /api/stats/import` - 导入数据
- `POST /api/stats/delete-by-date` - 按日期删除数据

### 系统配置接口
- `GET /api/getApiKey` - 获取API密钥（需密码验证）
- `POST /api/updateApiKey` - 更新API密钥
- `POST /api/verifyPassword` - 验证管理员密码
- `POST /api/updatePassword` - 更新管理员密码

## 生产部署建议

### 使用Gunicorn部署
```bash
# 使用配置文件启动
python start_server.py prod

# 或直接启动
gunicorn -c gunicorn.conf.py server:app
```

### 配置参数说明
- `workers = 8`：8个Worker进程
- `worker_class = "gevent"`：使用Gevent异步处理
- `worker_connections = 1000`：每个Worker最大1000连接
- `timeout = 120`：请求超时时间120秒
- `backlog = 2048`：请求队列长度

## 注意事项
1. 首次启动会自动创建SQLite数据库文件
2. 生产环境请务必修改默认管理员密码
3. AI功能需要配置DeepSeek API密钥
4. 建议定期备份数据库文件
