# Claude Code Web Agent - 用户手册

[English](USER_GUIDE.md) | 简体中文

本手册提供了 Claude Code Web Agent 的部署和使用的详细说明。

## 视频演示

观看 Claude Code Web Agent 的快速演示:

<video width="100%" controls>
  <source src="https://du7u4d2q1sjz6.cloudfront.net/cc_on_ac.mp4" type="video/mp4">
  您的浏览器不支持视频标签。[下载视频](https://du7u4d2q1sjz6.cloudfront.net/cc_on_ac.mp4)
</video>

---

## 目录

1. [部署指南](#部署指南)
2. [用户注册和登录](#用户注册和登录)
3. [Project 管理](#project-管理)
4. [创建 Session 与 Agent 对话](#创建-session-与-agent-对话)
5. [文件管理和预览](#文件管理和预览)
6. [Git 操作](#git-操作)
7. [Terminal 使用](#terminal-使用)
8. [Disconnect 和 Reconnect](#disconnect-和-reconnect)

---

## 部署指南

### 前置条件

在部署 Claude Code Web Agent 之前,请确保您具备:

- 已配置适当凭证的 **AWS CLI**
- 已安装 **Docker**(用于构建容器镜像)
- **Node.js 18+** 和 npm
- **jq**(JSON 处理器)
- **GitHub OAuth 应用程序**(用于仓库访问)

### 步骤 1: 配置部署设置

1. 导航到部署目录:
   ```bash
   cd deploy
   ```

2. 复制配置模板:
   ```bash
   cp config.env.template config.env
   ```

3. 编辑 `config.env` 并配置以下内容:
   - **AWS_REGION**: 您的 AWS 区域(例如 `us-west-2`)
   - **GITHUB_OAUTH_CLIENT_ID**: 来自您的 GitHub OAuth 应用
   - **GITHUB_OAUTH_CLIENT_SECRET**: 来自您的 GitHub OAuth 应用
   - **COGNITO_*** (可选): 留空以自动创建新的 Cognito 用户池
   - **AVAILABLE_MODELS**: Web 客户端的 model 列表(逗号分隔)
   - **Model 配置**: 可选,已提供默认值

### 步骤 2: 构建并推送 Docker 镜像

构建后端容器并推送到 Amazon ECR:

```bash
./deploy/01_build_and_push.sh
```

此脚本将:
- 创建 ECR 仓库
- 构建 ARM64 Docker 镜像(AgentCore 要求)
- 将镜像推送到 ECR

### 步骤 3: 部署 AgentCore Runtime

将后端部署到 Bedrock AgentCore:

```bash
./deploy/02_deploy_agentcore.sh
```

此脚本将:
- 创建或更新 AgentCore Runtime
- 创建 S3 workspace 存储桶
- 设置 Cognito User Pool(如果未提供)
- 创建具有所需权限的 IAM 执行角色
- 配置 GitHub OAuth provider
- 将配置导出到 `.agentcore_output`

### 步骤 4: 部署 Amplify Frontend

将 React frontend 部署到 AWS Amplify:

```bash
./deploy/03_deploy_amplify.sh
```

此脚本将:
- 创建或更新 Amplify app
- 构建并部署 React frontend
- 配置环境变量
- 自动更新 OAuth callback URL
- 提供 Amplify app URL

### 步骤 5: 更新 GitHub OAuth App

部署后,更新您的 GitHub OAuth App 设置:

1. 访问 https://github.com/settings/developers
2. 选择您的 OAuth App
3. 更新 **Authorization callback URL** 为:
   ```
   https://main.YOUR_AMPLIFY_DOMAIN/oauth/callback
   ```

### 快速部署

一次运行所有部署步骤:

```bash
./deploy/deploy_all.sh
```

---

## 用户注册和登录

### 了解认证系统

Claude Code Web Agent 使用 **AWS Cognito** 进行用户认证,提供安全的注册、登录和 session 管理。

### 注册新账户

1. **访问应用程序**: 导航到您部署的 Amplify URL(例如 `https://main.YOUR_AMPLIFY_DOMAIN`)

2. **点击 "Sign Up"**: 在登录页面底部点击 "Sign Up" 按钮

3. **填写注册表单**:
   - **Username**: 选择唯一的 username(字母、数字和下划线)
   - **Email**: 输入有效的电子邮件地址(将用于验证)
   - **Password**: 创建强密码(至少 8 个字符,包括大写、小写、数字和特殊字符)

4. **提交注册**: 点击 "Sign Up" 按钮

5. **邮箱验证**:
   - 检查您的邮箱收件箱以获取验证码
   - 在确认页面输入 6 位数验证码
   - 点击 "Confirm" 激活您的账户

6. **自动登录**: 成功确认后,您将自动登录

### 登录

1. **访问登录页面**: 导航到应用程序 URL

2. **输入凭证**:
   - **Username or Email**: 输入您的 username 或电子邮件地址
   - **Password**: 输入您的密码

3. **点击 "Sign In"**: 点击登录按钮进行身份验证

4. **Connection Modal**: 登录后,您将看到 "Connect to Server" modal
   - 点击 **"Connect to Server"** 启动后台服务并启用所有功能

### 登录问题排查

- **密码错误**: 仔细检查您的密码并重试
- **Email 未验证**: 检查您的电子邮件并完成验证
- **账户锁定**: 如果超过登录尝试次数,请联系管理员
- **忘记密码**: 使用 password reset 功能(如果已启用)

---

## Project 管理

### 了解 Project 和 Workspace

Claude Code Web Agent 中的 **Project** 是隔离的 workspace,您可以在其中处理不同的代码库。每个 project 都有:
- 位于 `/workspace/{project_name}` 的 working directory
- Git repository(可选)
- Session history
- 文件结构

### 创建新 Project

1. **导航到 Projects Tab**: 点击左侧边栏中的文件夹图标(📁)

2. **点击 "Create Project"**: 点击顶部的 "+ Create Project" 按钮

3. **输入 Project 详细信息**:
   - **Project Name**: 选择描述性名称(字母数字、连字符、下划线)
   - Project 将在 `/workspace/{project_name}` 中创建

4. **点击 "Create"**: 确认 project 创建

5. **自动切换**: 系统将自动切换到您的新 project

### 从 GitHub 导入

1. **导航到 Projects Tab**: 点击左侧边栏中的文件夹图标

2. **点击 "Import from GitHub"**: 找到 GitHub import 按钮

3. **使用 GitHub 进行身份验证**(仅首次):
   - 点击 header(右上角)中的 GitHub 图标
   - 授权应用程序访问您的 GitHub 账户
   - 等待确认(绿色勾选标记)

4. **输入 Repository URL**:
   - **HTTPS URL**: `https://github.com/username/repository.git`
   - **SSH URL**: `git@github.com:username/repository.git`(需要 SSH key 设置)
   - **可选**: 指定 branch 名称(默认为 main branch)
   - **可选**: 启用 shallow clone 以加快克隆速度

5. **点击 "Clone"**: 开始克隆过程

6. **监控进度**: 在 console 中观察克隆进度

7. **自动切换**: 成功克隆后,project 将被激活

### 在 Project 之间切换

1. **打开 Project Switcher**:
   - 点击 header 中的 project 名称(显示当前 project 或 "Default Workspace")
   - 或点击 sidebar 中的文件夹图标并从列表中选择 project

2. **选择 Project**: 点击列表中的任何 project

3. **确认切换**(如果您有 active session):
   - 警告: 切换将关闭您当前的 session
   - 点击 "OK" 继续

4. **自动备份**: 在切换之前,您当前的 project 会自动备份到 S3

5. **Project 激活**: 新 project 的 workspace 已加载并准备使用

### Project 功能

- **自动 S3 Backup**: 切换时 project 自动同步到 S3
- **隔离 Session**: 每个 project 都有自己的 session history
- **Working Directory**: Project 有专用的 working directory
- **Git 集成**: 每个 project 完整的 git 支持
- **File Browser**: 在每个 project 中浏览和管理文件

---

## 创建 Session 与 Agent 对话

### 了解 Session

**Session** 表示与 Claude agent 的对话。每个 session 维护:
- 对话历史
- Agent context 和 memory
- Tool 使用历史
- Working directory context

### 创建新 Session

1. **导航到 Sessions Tab**: 点击左侧边栏中的聊天图标(💬)

2. **点击 "New Session"**(或 + 按钮):
   - 如果您没有 active session,按钮将显示 "Start Session"
   - 如果您有 active session,它将显示 "Clear Session"

3. **Session 初始化**:
   - 生成唯一的 session ID
   - Agent 使用您的 working directory context 进行初始化
   - 您将在聊天中看到 "✅ Connected to Claude Agent"

4. **Session 信息**: Session ID 显示在聊天 header 中

### 与 Agent 对话

1. **输入您的消息**: 在底部的输入框中输入您的请求:
   ```
   创建一个读取 CSV 文件并生成摘要报告的 Python 脚本
   ```

2. **Send Message**: 点击 send 按钮(➤)或按 Enter 键

3. **Agent 响应**: Agent 将:
   - 实时流式传输其响应
   - 根据需要使用 tools(文件操作、terminal 命令等)
   - 在聊天中显示 tool 使用(例如 "Using tool: Edit")

4. **查看输出**: 检查 agent 的文本响应和 tool 输出

### Permission 系统

Agent 在执行某些操作时需要 permission:

1. **Permission Request 出现**: 当 agent 需要执行写操作时,您将看到黄色 permission 框

2. **审查 Request**:
   - **Tool Name**: 正在使用的 tool(例如 "Edit"、"Write")
   - **Parameters**: 操作的详细信息(文件路径、内容等)
   - **Suggested Changes**: Agent 想要修改的内容

3. **授予或拒绝 Permission**:
   - **✓ Allow**: 授予此操作的 permission
   - **⚡ Apply Suggestions**: 应用建议的更改并授予 permission
   - **✗ Deny**: 拒绝该操作

4. **继续对话**: 在您做出决定后,agent 继续

### Model 选择

您可以在 session 期间切换 model:

1. **当前 Model**: 显示在聊天 header 中(例如 "sonnet-4-5-...")

2. **点击 Model 名称**: 打开 model selector dropdown

3. **选择 Model**: 从可用 model 中选择:
   - **Claude Sonnet 4.5**: 最适合复杂推理和编码
   - **Claude Haiku 4.5**: 更快,适合简单任务
   - **Qwen Coder**: 专门用于编码任务

4. **Model 切换**: Agent 将为后续消息使用新 model

### 管理 Session

**恢复先前的 Session**:
1. 导航到 Sessions Tab
2. 点击 session list 中的任何 session
3. 对话历史将被加载

**清除当前 Session**:
1. 在 Sessions Tab 中点击 "Clear Session"
2. 确认操作
3. 创建新 session,丢失当前 context

**Session 持久性**:
- Session 自动保存到磁盘
- 即使在 disconnect 后也可以恢复 session
- 每个 session 文件存储在 `~/.claude/projects/` 中

---

## 文件管理和预览

### 了解 File Browser

**File Browser** 显示您当前 project 的文件结构,允许您导航、预览和管理文件。

### 浏览文件

1. **访问 File Browser**: 点击左侧边栏中的文件图标(📄)

2. **浏览目录**:
   - 点击文件夹名称以展开/折叠它们
   - 当前路径显示在顶部
   - 使用 breadcrumb navigation 向上导航目录

3. **文件图标**:
   - 📁 Folder
   - 📄 File
   - 🔧 Configuration file(.json、.yaml、.toml 等)
   - 🐍 Python file(.py)
   - 📜 JavaScript file(.js、.jsx、.ts、.tsx)

### 预览文件

1. **点击文件**: 点击 file browser 中的任何文件名

2. **Preview Panel 打开**: 右侧出现 preview panel

3. **文件内容显示**:
   - **文本文件**: 显示 syntax-highlighted 内容
   - **图像**: 显示图像
   - **大文件**: 显示第一部分,带有 "Load More" 选项

4. **Syntax Highlighting**: 自动检测代码文件的语言

5. **关闭 Preview**: 点击 preview header 中的 ✗ 按钮

### 通过 Agent 进行文件操作

您可以要求 agent 执行文件操作:

```
创建一个名为 main.py 的新文件,包含 Hello World 程序
```

```
读取 config.json 的内容并解释每个设置的作用
```

```
修改 utils.py 以向 process_data 函数添加错误处理
```

### 文件刷新

- **自动刷新**: 当您向 agent 发送消息时,文件会自动刷新
- **手动刷新**: Agent 操作后 file browser 更新
- **实时更新**: Agent 所做的更改立即显示

---

## Git 操作

### 了解 Git 集成

**Git Panel** 提供版本控制功能,允许您查看更改、创建 commit 和 push 到远程仓库。

### 查看 Git Status

1. **访问 Git Tab**: 点击左侧边栏中的 git branch 图标

2. **Git Status 显示**:
   - **Current Branch**: 在 header 中显示为 badge
   - **Staged Files**: 准备 commit 的文件(绿色 +)
   - **Unstaged Files**: 尚未 stage 的修改文件(蓝色 M)
   - **Untracked Files**: 不在 git 中的新文件(📄)

3. **文件更改图标**:
   - **M**(Modified): 文件已更改
   - **A**(Added): 新文件已 stage
   - **D**(Deleted): 文件已被删除

4. **自动刷新**: 当您切换到 Git tab 时,git status 会刷新

### 查看 Commit History

1. **Recent Commits 部分**: 向下滚动以查看最近的 commit

2. **Commit 信息**:
   - **Commit Hash**: 短 hash(前 7 个字符)
   - **Author**: 谁进行了 commit
   - **Date**: Commit 时间
   - **Message**: Commit message

3. **展开 Commit**: 点击任何 commit 以查看更改的文件

4. **文件更改**: 显示该 commit 中修改了哪些文件

### 创建 Commit

1. **查看更改**: 检查 "Changes" 部分中的文件

2. **点击 "Commit" 按钮**: 打开 commit form

3. **编写 Commit Message**:
   - 第一行: 简要摘要(建议最多 50 个字符)
   - 空行(可选)
   - 详细描述(如果需要)

4. **选择文件**(可选):
   - 默认情况下,包括所有更改的文件
   - 取消选中您不想 commit 的文件
   - 或保留所有选中以 commit 所有内容

5. **点击 "Create Commit"**: 完成 commit

6. **确认**: 您将看到 "✓ Commit created successfully"

### Push 到 Remote

1. **确保存在 Commit**: 检查您是否有要 push 的本地 commit

2. **点击 "Push" 按钮**: 位于 Recent Commits 部分

3. **确认 Push**: 出现确认对话框

4. **GitHub 身份验证**(如果需要):
   - 如果未经身份验证,系统将提示您使用 GitHub 进行身份验证
   - 遵循 GitHub OAuth 流程

5. **Push 进度**: 等待 push 完成

6. **成功消息**: "Successfully pushed commits"

### 通过 Agent 进行 Git 操作

您也可以要求 agent 执行 git 操作:

```
显示 git status
```

```
创建一个 commit message 为 "Add user authentication feature" 的 commit
```

```
将我的更改 push 到 remote repository
```

### 手动刷新

- **Refresh 按钮**: 点击 Git panel header 中的 refresh 图标(🔄)
- **刷新**: Git status 和 commit history
- **使用场景**: 在外部 git 操作后更新

---

## Terminal 使用

### 了解集成 Terminal

**Terminal** 提供在服务器上运行的全功能命令行界面,允许您执行命令、运行脚本并与 workspace 交互。

### 打开 Terminal

1. **点击 Terminal 图标**: 点击 header(右上角)中的 terminal 图标(⌨️)

2. **Terminal Panel 打开**: Terminal panel 从右侧滑入

3. **初始状态**: Terminal 在您当前的 project directory 中初始化

### 使用 Terminal

1. **运行命令**: 输入任何 shell 命令并按 Enter 键:
   ```bash
   ls -la
   ```
   ```bash
   python script.py
   ```
   ```bash
   npm install
   ```

2. **输出显示**: 命令输出实时显示

3. **颜色支持**: 支持 ANSI colors 以提高可读性

4. **Command History**:
   - 按 ↑ 键循环浏览先前的命令
   - 按 ↓ 键在 history 中前进

5. **Tab Completion**: Tab 键用于 auto-completion(如果 shell 支持)

### Terminal 功能

- **Working Directory**: 始终从您当前的 project directory 开始
- **Environment**: 具有所有系统工具的完整 shell environment
- **长时间运行的命令**: 支持无限期运行的命令
- **交互式程序**: 可以运行 vim、nano 等交互式程序
- **多行**: 支持多行输入(使用 Shift+Enter)

### 常见用例

**包管理**:
```bash
npm install express
pip install requests
uv add anthropic
```

**运行脚本**:
```bash
python main.py
node server.js
./run_tests.sh
```

**Git 操作**:
```bash
git status
git pull origin main
git log --oneline -10
```

**文件操作**:
```bash
cat config.json
grep -r "TODO" src/
find . -name "*.py"
```

**构建和测试**:
```bash
npm run build
pytest tests/
cargo build --release
```

### 调整 Terminal 大小

1. **Resize Handle**: 将鼠标放在 terminal panel 的左边缘

2. **拖动以调整大小**: 点击并向左或向右拖动以调整宽度

3. **大小限制**: Terminal 宽度限制在 400px 到 1000px 之间

### 关闭 Terminal

1. **再次点击 Terminal 图标**: 关闭 terminal

2. **或点击 ✗**: 点击 terminal header 中的 close 按钮

3. **Session 持续**: Terminal session 在后台保持活动

---

## Disconnect 和 Reconnect

### 了解连接状态

Claude Code Web Agent 有两种连接状态:
- **Server Connected**: 后台服务运行,可以使用所有功能
- **Server Disconnected**: 后台服务已停止,功能有限

### Disconnect 与 Server 的连接

Disconnect 会停止所有后台服务,但保持您的登录状态。

1. **点击 Disconnect 按钮**: 点击 header 中的 ✗ 圆圈图标

2. **确认 Disconnect**: 出现确认对话框:
   ```
   Disconnect from server?

   This will stop all background requests and close any active sessions.
   ```

3. **点击 "OK"**: 确认 disconnect 操作

4. **Disconnect 过程**:
   - 当前 agent session 已关闭(如果 active)
   - 等待 3 秒以完成待处理的请求
   - 停止 AgentCore runtime session
   - 后台服务(health check、polling)已停止

5. **Disconnect Modal 出现**: 您将看到带有选项的 connection modal:
   - **Connect to Server**: Reconnect 并恢复工作
   - **Force Stop AgentCore**: 紧急停止(如果需要)
   - **Log Out**: 退出应用程序

### Reconnect 到 Server

1. **点击 "Connect to Server"**: 在 disconnect modal 上

2. **后台服务启动**:
   - Health check polling 恢复
   - Session polling 恢复
   - API connection 已建立

3. **准备使用**: 现在所有功能都可用

4. **自动恢复**: 保留您之前的 project 和设置

### Logout

Logout 会停止所有服务并结束您的 session。

1. **点击 Logout 按钮**: 点击 header 中的 logout 图标

2. **确认 Logout**: 出现确认对话框:
   ```
   Logout?

   This will stop all background requests, close any active sessions, and log you out.
   ```

3. **点击 "OK"**: 确认 logout 操作

4. **Logout 过程**:
   - Disconnect active agent session
   - 等待 3 秒以完成待处理的请求
   - 停止 AgentCore runtime session
   - 从 Cognito sign out

5. **重定向到 Login**: 您被重定向到登录页面

### Force Stop AgentCore(紧急)

如果系统无响应,您可以 force stop:

1. **访问 Disconnect Modal**: 首先 disconnect 与 server 的连接

2. **点击 "Force Stop AgentCore"**: Modal 中的红色按钮

3. **确认操作**: 这将立即停止 runtime session

4. **使用场景**: 仅在正常 disconnect 失败时使用

### Reconnect 场景

**Disconnect 后**:
- 保留所有设置
- 保留 project 选择
- 没有 active session(必须创建新 session)
- 后台服务重新启动

**Logout 后**:
- 必须重新登录
- 设置保留在浏览器中
- 保留 project 选择
- 没有 active session

**Force Stop 后**:
- 必须 reconnect 到 server
- 可能需要等待几秒钟以重新启动 runtime
- 保留所有状态

### 最佳实践

- **正常工作**: 保持 server connected
- **长时间休息**: Disconnect 以节省资源
- **一天结束**: 为了安全而 logout
- **切换用户**: 始终先 logout
- **故障排除**: 将 force stop 作为最后手段

---

## 提示和最佳实践

### Session 管理

- **创建描述性 session 名称**: 使用清晰的命名以便轻松识别
- **恢复旧 session**: 在不丢失 context 的情况下继续之前的工作
- **在开始新任务时 clear**: 为不相关的工作重新开始

### 文件组织

- **为不同的 repository 使用 project**: 保持代码库分离
- **定期 commit**: 使用清晰的 message 频繁 commit
- **备份到 S3**: Project 切换会自动备份到 S3

### Agent 交互

- **具体**: 向 agent 提供清晰、详细的指令
- **审查 permission**: 始终审查 agent 想要更改的内容
- **使用 context**: 引用文件和先前的对话 context

### 性能

- **关闭未使用的 panel**: 不需要时隐藏 preview 和 terminal
- **空闲时 disconnect**: 在休息期间节省资源
- **使用适当的 model**: 简单任务使用 Haiku,复杂任务使用 Sonnet

### 安全

- **在共享计算机上 logout**: 完成后始终 logout
- **审查文件更改**: 在 commit 之前检查 agent 修改的内容
- **不要共享凭据**: 永远不要共享您的登录凭据

---

## 故障排除

### 无法 Connect 到 Server

- **检查 URL**: 验证 Amplify URL 是否正确
- **检查部署**: 确保 AgentCore runtime 已部署
- **检查日志**: 查看浏览器 console 中的错误

### Session 创建失败

- **Server disconnected**: 首先 connect 到 server
- **检查权限**: 确保 IAM role 配置正确
- **检查 Bedrock 访问**: 在 Bedrock console 中验证 model 访问

### 文件操作失败

- **检查权限**: 文件系统 permission 可能受到限制
- **检查磁盘空间**: S3 bucket 可能已满
- **刷新浏览器**: 尝试刷新页面

### Git 操作失败

- **GitHub 身份验证**: 点击 GitHub 图标并进行身份验证
- **检查 repository**: 验证 repository URL 是否正确
- **检查凭据**: 可能需要重新进行身份验证

### Terminal 不工作

- **重新加载页面**: 尝试刷新浏览器
- **检查连接**: 确保 server 已 connected
- **检查防火墙**: 企业防火墙可能会阻止 WebSocket 连接

---

## 支持和资源

### 文档

- **README.md**: 架构和部署概述
- **WORKSPACE_SYNC.md**: Workspace 管理详细信息
- **Backend 文档**: `backend/` 目录中的 API 参考

### 获取帮助

- **GitHub Issues**: 报告错误并请求功能
- **AWS 支持**: 就基础设施问题联系 AWS 支持
- **社区**: 加入 project 论坛的讨论

### 其他资源

- **AWS Bedrock 文档**: https://docs.aws.amazon.com/bedrock/
- **Claude API 文档**: https://docs.anthropic.com/
- **AWS Amplify 文档**: https://docs.aws.amazon.com/amplify/

---

**版本**: 1.0.0
**最后更新**: 2025-01-13
