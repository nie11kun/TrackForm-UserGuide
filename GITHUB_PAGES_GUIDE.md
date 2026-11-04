# GitHub Pages 自动化部署与自定义域名完整配置指南

本文档面向项目维护人员，系统讲解如何将静态文档项目（如 HonKit、VitePress、Docusaurus、Hugo 等）通过 **GitHub Actions** 自动化构建并发布到 **GitHub Pages**，并结合 **Cloudflare** 实现免运维的自定义二级域名访问与 HTTPS 加密。

---

## 目录

- [一、部署架构全景图](#一部署架构全景图)
- [二、GitHub Actions 自动化 CI/CD 工作流配置](#二github-actions-自动化-cicd-工作流配置)
  - [1. 工作流文件 `.github/workflows/deploy.yml`](#1-工作流文件-githubworkflowsdeployyml)
  - [2. 关键配置项逐行剖析](#2-关键配置项逐行剖析)
- [三、GitHub 仓库设置（Settings -> Pages）](#三github-仓库设置settings---pages)
- [四、Cloudflare 自定义域名配置实战](#四cloudflare-自定义域名配置实战)
  - [1. CNAME 解析记录填写规范](#1-cname-解析记录填写规范)
  - [2. 核心避坑：小黄云（Proxied）与灰色云朵（DNS only）的切换策略](#2-核心避坑小黄云proxied与灰色云朵dns-only的切换策略)
- [五、常见故障排查手册（Troubleshooting）](#五常见故障排查手册troubleshooting)
  - [1. 报错：Branch 中找不到 `gh-pages` 分支](#1-报错branch-中找不到-gh-pages-分支)
  - [2. 报错：GitHub Actions 失败，提示 403 权限不足](#2-报错github-actions-失败提示-403-权限不足)
  - [3. 报错：`InvalidDNSError` 或 `Domain's DNS record could not be retrieved`](#3-报错invaliddnserror-或-domains-dns-record-could-not-be-retrieved)
  - [4. 报错：`Domain is not eligible for HTTPS at this time`](#4-报错domain-is-not-eligible-for-https-at-this-time)
  - [5. 现象：GitHub 显示部署成功且证书正常，但本地浏览器打不开](#5-现象github-显示部署成功且证书正常但本地浏览器打不开)
- [六、高级排障与命令行调试工具箱](#六高级排障与命令行调试工具箱)

---

## 一、部署架构全景图

现代静态文档站点在 GitHub 上的标准工程实践采用 **“源码 + 产物双分支隔离”** 架构：

```text
┌────────────────────────────────────────────────────────┐
│                   GitHub 远程仓库                      │
│                                                        │
│  main 分支（开发分支）                                  │
│  ├── Markdown 源文档 (.md)                              │
│  ├── 配置文件 (book.json / package.json)               │
│  └── 自动化工作流 (.github/workflows/deploy.yml)       │
└──────────────────────────┬─────────────────────────────┘
                           │ 开发者 push 触发
                           ▼
┌────────────────────────────────────────────────────────┐
│                   GitHub Actions CI                    │
│                                                        │
│  1. 拉取代码 (Checkout)                                 │
│  2. 安装 Node.js 20 与项目依赖 (npm install)            │
│  3. 编译静态 HTML (npx honkit build -> 输出到 _book/)   │
│  4. 自动写入 CNAME 并推送到目标分支                    │
└──────────────────────────┬─────────────────────────────┘
                           │ 自动发布产物
                           ▼
┌────────────────────────────────────────────────────────┐
│  gh-pages 分支（纯静态发布分支）                       │
│  ├── index.html                                        │
│  ├── CNAME (trackform-manual.niekun.net)               │
│  └── 静态资源 (css / js / images)                      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                 GitHub Pages 边缘服务器                │
│             + Cloudflare 全球 CDN 缓存加速             │
│                                                        │
│       终端用户通过 https://trackform-manual.niekun.net/  │
└────────────────────────────────────────────────────────┘
```

* **优点**：
  1. `main` 分支保持干净，只有纯源码，没有构建产生的杂乱 HTML 文件；
  2. 每次本地修改推送到 `main` 分支后，云端自动编译发布，完全不用手动打包和复制文件；
  3. 自定义域名文件（`CNAME`）由工作流自动注入，不会因为每次重新构建而被覆盖丢失。

---

## 二、GitHub Actions 自动化 CI/CD 工作流配置

### 1. 工作流文件 `.github/workflows/deploy.yml`

在项目根目录下创建文件 `.github/workflows/deploy.yml`，完整标准配置如下：

```yaml
name: Deploy Honkit to GitHub Pages

on:
  push:
    branches:
      - main  # 仅当推送或合并到 main 分支时触发

# 赋予 GitHub Actions 写回仓库分支的权限（至关重要！）
permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Code
      uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'  # 推荐使用 Node.js 20 LTS

    - name: Install Dependencies
      run: npm install

    - name: Build Honkit
      run: npx honkit build

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./_book                      # 静态产物目录
        cname: trackform-manual.niekun.net       # 绑定的自定义域名
```

### 2. 关键配置项逐行剖析

* **`permissions: contents: write`**：
  * **背景**：自 2023 年起，GitHub 将 Actions 默认的 `GITHUB_TOKEN` 权限收紧为“只读（Read only）”。
  * **作用**：必须显式声明 `contents: write`，Actions 才有权限自动创建并推送代码到 `gh-pages` 分支，否则工作流在最后一步会直接报错 `403 Resource not accessible by integration`。
* **`node-version: '20'`**：
  * **避坑要点**：请使用 Node.js 20 或更新版本。若使用较老的 Node.js 18，现代前端依赖（如 `undici`）会报错 `ReferenceError: File is not defined` 导致构建崩溃。
* **`uses: peaceiris/actions-gh-pages@v3`**：
  * 业界最广泛使用的 GitHub Pages 发布 Action。它会自动处理 Git 认证、清空并复写 `gh-pages` 分支。
* **`cname: trackform-manual.niekun.net`**：
  * 此处配置后，Action 在部署到 `gh-pages` 时会自动在根目录下生成合规的 `CNAME` 文件，确保每次部署都不会丢失自定义域名绑定。

---

## 三、GitHub 仓库设置（Settings -> Pages）

当上述 GitHub Actions **首次成功运行**之后，需要到仓库后台做一次初始绑定确认：

1. 打开 GitHub 仓库主页，点击顶部导航栏的 **Settings**；
2. 在左侧菜单栏找到 **Pages**（路径为：`Settings -> Code and automation -> Pages`）；
3. **Build and deployment（构建与部署源）**：
   * **Source**：选择 **`Deploy from a branch`**；
   * **Branch**：左侧下拉框选择 **`gh-pages`**，右侧目录保持 **`/ (root)`**，点击 **Save**。
4. **Custom domain（自定义域名）**：
   * 正常情况下，由于我们在 Actions 中配置了 `cname`，系统会自动填入 `trackform-manual.niekun.net` 并显示 **DNS check in progress...** 或 **DNS check successful**。
5. **Enforce HTTPS**：
   * 等待 DNS 校验通过、证书签发成功后，勾选 **Enforce HTTPS**，系统将强制所有 HTTP 访问自动重定向为安全的 HTTPS。

---

## 四、Cloudflare 自定义域名配置实战

由于域名通常托管在 Cloudflare、阿里云或腾讯云等 DNS 提供商，配置自定义二级域名的核心是建立一条标准的 **CNAME 记录**。

### 1. CNAME 解析记录填写规范

登录 Cloudflare 控制台 -> 选择主域名（如 `niekun.net`）-> **DNS** -> **Records** -> 点击 **Add record**：

| 表单字段 | 填写内容 | 说明与常见避坑 |
| :--- | :--- | :--- |
| **Type（类型）** | **`CNAME`** | 必须是 CNAME 别名记录，不能是 A 记录。 |
| **Name（名称）** | **`trackform-manual`** | **极其重要**：仅输入二级域名的前缀部分！下方预览会自动显示为 `trackform-manual.niekun.net`。<br>❌ 错误做法：直接粘贴完整域名，部分控制台会自动拼接导致变成 `trackform-manual.niekun.net.niekun.net`。 |
| **Target（目标）** | **`nie11kun.github.io`** | **极其重要**：必须填您的 **GitHub 用户名/组织名主页** `[username].github.io`，末尾**不要加**仓库名（不要写成 `nie11kun.github.io/TrackForm-UserGuide`）！ |
| **Proxy status（代理状态）** | 详见下方策略 | 首次签发时切为**灰色云朵（DNS only）**；证书就绪后切回**橙色小黄云（Proxied）**。 |
| **TTL** | `Auto` | 保持默认自动即可。 |

### 2. 核心避坑：小黄云（Proxied）与灰色云朵（DNS only）的切换策略

这是 Cloudflare 配合 GitHub Pages 时**最容易导致报错的隐藏机制**：

```text
【阶段一：初次绑定与申请证书】
Cloudflare DNS: [灰色云朵 DNS only] ──> 直接暴露 GitHub 官方 CNAME ──> GitHub/Let's Encrypt 验证成功，签发证书

【阶段二：日常运营与 CDN 加速】
Cloudflare DNS: [点亮橙色云朵 Proxied] ──> Cloudflare 边缘节点代理 ──> 国内极速访问，抵御网络阻断
```

#### 为什么不能从一开始就开小黄云？
* GitHub Pages 申请由 Let's Encrypt 签发的免费 SSL 证书时，GitHub 的校验机器人会发起真实的 DNS 与 HTTP 探针验证所有权。
* 如果一开始就开着小黄云（Proxied），Cloudflare 会拦截所有流量并返回 Cloudflare 自己的 Anycast CDN IP（如 `104.21.x.x`）。GitHub 检测不到直接的 CNAME 指向，就会报错：
  `Domain's DNS record could not be retrieved (InvalidDNSError)`，并拒绝签发证书。

#### 正确的“两阶段操作法则”：
1. **阶段一（首次配置）**：
   * 将 Cloudflare 记录设为 **`DNS only`（灰色云朵）**，保存；
   * 到 GitHub 仓库的 **Settings -> Pages** 填入自定义域名并保存；
   * 等待 2~5 分钟，直到 GitHub 页面显示绿色的 **`DNS check successful`** 且 **`https_certificate: approved`**。
2. **阶段二（日常加速）**：
   * 确认 HTTPS 已经生效后，回到 Cloudflare 将记录切换回 **`Proxied`（点亮橙色小黄云）**；
   * 此时既保留了 GitHub 的正规证书，又享受了 Cloudflare 全球节点的 CDN 缓存加速，国内访问极速且稳定。

---

## 五、常见故障排查手册（Troubleshooting）

### 1. 报错：Branch 中找不到 `gh-pages` 分支
* **原因**：GitHub 仓库在新建时只有一个 `main` 分支。在 GitHub Actions 首次成功构建并推送前，远程仓库中**根本不存在** `gh-pages` 这个分支。
* **解决步骤**：
  1. 无需手动在本地 `git checkout -b gh-pages`；
  2. 只要确保项目代码成功推送到 `main` 分支；
  3. 前往仓库的 **Actions** 标签页，等待名为 `Deploy Honkit to GitHub Pages` 的工作流显示绿色勾号（成功）；
  4. 刷新 **Settings -> Pages** 页面，下拉菜单中就会自动出现 `gh-pages` 分支。

### 2. 报错：GitHub Actions 失败，提示 403 权限不足
* **典型日志**：
  ```text
  remote: Permission to <user>/<repo>.git denied to github-actions[bot].
  fatal: unable to access '...': The requested URL returned error: 403
  ```
* **解决步骤**：
  1. 检查 `.github/workflows/deploy.yml` 中是否包含了 `permissions: contents: write`；
  2. 进入 GitHub 仓库：**Settings -> Actions -> General**；
  3. 滑动到底部找到 **Workflow permissions**；
  4. 将默认的 *Read repository contents permission* 改选为 **`Read and write permissions`** 并点击 Save。

### 3. 报错：`InvalidDNSError` 或 `Domain's DNS record could not be retrieved`
* **原因分析**：GitHub 无法在公网检索到该域名的 CNAME 解析。
* **解决步骤**：
  1. 检查 Cloudflare 中 Name 字段是否多填了域名后缀；
  2. 检查 Cloudflare 中当前是否开着小黄云，如果是，请**临时切换为灰色云朵（DNS only）**；
  3. 在终端使用公共 DNS 验证是否生效：
     ```powershell
     curl.exe -s "https://dns.google/resolve?name=trackform-manual.niekun.net&type=CNAME"
     ```
     若返回中 `data` 包含了 `nie11kun.github.io.` 则说明公网 DNS 已经完全就绪。此时在 GitHub Pages 页面点击 **Check again** 即可变绿。

### 4. 报错：`Domain is not eligible for HTTPS at this time`
* **原因分析**：域名 DNS 刚刚生效，Let's Encrypt 证书颁发机构还在排队生成证书（通常需要 2 ~ 15 分钟）。
* **解决步骤**：
  * 只要上一步的 DNS Check 已经是绿色成功状态，请耐心等待 10 分钟；
  * 如果超过 30 分钟未就绪，可在 GitHub Pages 页面先点击 **Remove** 移除自定义域名，重新输入并保存，强行触发证书重新签发。

### 5. 现象：GitHub 显示部署成功且证书正常，但本地浏览器打不开
* **典型特征**：使用命令行 `curl` 测试能返回 200 OK，但浏览器访问提示“找不到服务器”或连接超时。
* **原因分析**：**本地 DNS 负缓存（Negative Cache）**。在刚配置域名尚未生效时，浏览器或本机运行的代理工具（如 Clash、Sing-box、TUN 虚拟网卡等）把“查询失败”的结果缓存了 10~30 分钟。
* **解决步骤**：
  1. **清除 Windows 本地 DNS 缓存**：
     ```powershell
     ipconfig /flushdns
     ```
  2. **清除代理软件缓存**：若使用 Clash，点击设置中的 **Restart Core（重启核心）** 或 **Flush DNS / Clear Fake-IP**；
  3. **使用隐私模式访问**：打开浏览器的**无痕窗口（Incognito）**直接访问目标网址。

---

## 六、高级排障与命令行调试工具箱

熟练使用以下命令行工具，可以 10 秒内准确定位任何 Pages 部署与网络解析问题：

### 1. 查询当前仓库 GitHub Pages 与证书底层状态
使用 GitHub CLI 命令直接查看 GitHub 官方对该域名的认定状态：
```powershell
gh api repos/nie11kun/TrackForm-UserGuide/pages
```
* **正常返回示例**：
  ```json
  {
    "status": "built",
    "cname": "trackform-manual.niekun.net",
    "https_certificate": {
      "state": "approved",
      "description": "The certificate has been approved."
    },
    "https_enforced": true
  }
  ```
  若 `state` 为 `approved`，说明服务端配置 100% 成功，所有打不开的问题均来自客户端网络或本地 DNS 缓存。

### 2. 使用 Google DoH（DNS-over-HTTPS）跳过本地污染查公网解析
无需等待本地 DNS 刷新，直接查询 Google 全球 DNS 节点的解析结果：
```powershell
# 查询 CNAME 指向
curl.exe -s "https://dns.google/resolve?name=trackform-manual.niekun.net&type=CNAME"

# 查询最终 A 记录 IP
curl.exe -s "https://dns.google/resolve?name=trackform-manual.niekun.net&type=A"
```

### 3. 绕过本地解析，直连 GitHub 官方节点验证 HTTP 响应
使用 curl 的 `--resolve` 参数强行将域名绑定到 GitHub 官方 IP 进行端到端握手测试：
```powershell
curl.exe -Iv https://trackform-manual.niekun.net/ --resolve "trackform-manual.niekun.net:443:185.199.108.153"
```
若末尾返回 `< HTTP/1.1 200 OK`，证明 GitHub 端的网站和 HTTPS 已经万无一失。
