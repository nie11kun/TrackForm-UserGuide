# HonKit 用户手册维护与操作指南

本文档面向 **TrackForm-UserGuide** 维护人员，介绍如何在本地预览、编译、导出 PDF、新增章节、更新配图以及通过 GitHub Pages 自动发布在线文档。

---

## 一、环境准备与依赖安装

本项目基于 **Node.js** 与 **HonKit** 构建。首次克隆仓库或更换电脑后，在项目根目录执行以下命令安装依赖：

```powershell
# 1. 进入项目根目录
cd "C:\Users\Marco Nie\Development\WorkProgram\TrackForm-UserGuide"

# 2. 安装 package.json 中声明的 HonKit 及插件（如 honkit-plugin-katex）
npm install
```

> **提示**：要求本地已安装 Node.js（推荐 v18 LTS 或更高版本）。

---

## 二、日常高频 HonKit 命令速查

### 1. 本地实时预览（热重载开发模式）
在编写或修改 `.md` 文档时，启动本地预览服务器：

```powershell
npx honkit serve
```
* 启动成功后，在浏览器访问：**http://localhost:4000**
* 当您保存任何 `.md` 文件或修改 `SUMMARY.md` 时，浏览器页面会自动刷新。
* 按 `Ctrl + C` 可停止预览服务。

### 2. 编译生成静态网站（HTML）
将全部 Markdown 文档与图片编译为静态网页（输出到 `_book/` 目录）：

```powershell
npx honkit build
```
* 编译完成后，所有的静态网页、样式与图片资源均位于 `_book/` 文件夹下。

### 3. 导出离线 PDF 手册（可选）
如果需要生成单文件离线版 `output.pdf`（需本地已安装 [Calibre](https://calibre-ebook.com/download) 并将其中的 `ebook-convert` 加入系统环境变量 `PATH`）：

```powershell
npx honkit pdf ./ ./output.pdf
```
对应的电子书格式导出命令：
* 导出 EPUB：`npx honkit epub ./ ./output.epub`
* 导出 MOBI：`npx honkit mobi ./ ./output.mobi`

---

## 三、文档目录结构与配置文件说明

```text
TrackForm-UserGuide/
├── book.json               # HonKit 核心配置文件（标题、语言、KaTeX 数学公式插件等）
├── package.json            # Node.js 依赖清单（honkit, honkit-plugin-katex）
├── SUMMARY.md              # 【核心】左侧目录树定义文件（决定章节顺序与层级）
├── README.md               # 手册首页（对应“介绍”章节）
├── CNAME                   # 自定义域名文件（trackform-manual.niekun.net）
├── .bookignore             # HonKit 编译忽略列表（排除 tools/、node_modules/ 等非正文文件）
├── styles/
│   ├── website.css         # 网页端自定义样式
│   └── pdf.css             # PDF 导出自定义样式
├── tools/
│   └── build_images.py     # 本地自动化配图生成脚本（已被 .gitignore 与 .bookignore 忽略）
├── 1_getting_started/      # 第 1 章 Markdown 及 resources/ 配图
├── 2_basic_params/         # 第 2 章 Markdown 及 resources/ 配图
...
└── 9_troubleshooting/      # 第 9 章 Markdown 及 resources/ 配图
```

---

## 四、如何修改或新增章节？

### 1. 修改现有章节
直接用 VS Code 或其它 Markdown 编辑器打开对应章节目录下的 `.md` 文件修改保存即可。

* **数学公式写法**（已启用 `honkit-plugin-katex`）：
  * 行内公式使用单个 `$` 包裹，例如：`$\alpha = 42^\circ$`
  * 独立成行的块级公式使用 `$$` 包裹，例如：
    ```markdown
    $$\text{z\_端面} = \text{z\_球心} + \text{球心距 } L$$
    ```
* **图片引用写法**：
  建议统一将本章节图片放入本章节目录的 `resources/` 文件夹下，并使用相对路径引用：
  ```markdown
  ![图片说明](resources/xxx.png)
  ```

### 2. 新增一个章节页面
1. 在对应文件夹下新建 `.md` 文件（例如 `8_workflows_cases/case5_custom.md`）；
2. 打开根目录下的 **`SUMMARY.md`**，在对应位置添加一行目录链接：
   ```markdown
   * [典型设计实战案例](8_workflows_cases/README.md)
       * [案例一：椭圆截面成型刀与单圆弧设计](8_workflows_cases/case1_ellipse.md)
       ...
       * [案例五：自定义拓展案例](8_workflows_cases/case5_custom.md)
   ```
3. 运行 `npx honkit build` 或观察 `npx honkit serve` 即可看到左侧导航栏已新增该小节。

---

## 五、如何重新生成全套软件配图？

当 `TrackForm` 软件界面或默认参数发生更新时，无需手动截图，可直接运行本地配图生成脚本一键更新全套 59 张高清配图：

```powershell
python tools/build_images.py
```

* 该脚本会自动调用同级目录 `..\TrackForm` 的提示卡片绘图与图表渲染接口，将生成的 PNG 图片输出到各章节的 `resources/` 目录下。
* 注意：`tools/` 目录仅保存在本地开发环境中，已在 `.gitignore` 和 `.bookignore` 中配置忽略，不会上传到公开仓库或编译到网页中。

---

## 六、发布与自动部署流程（GitHub Pages）

本项目已配置 GitHub Actions 自动构建与部署工作流（`.github/workflows/deploy.yml`）。

### 1. 日常更新发布三步曲
每次修改完文档或更新配图后，只需在终端执行标准 Git 推送命令：

```powershell
# 1. 查看改动文件
git status

# 2. 暂存并提交改动
git add -A
git commit -m "docs: 更新用户手册内容"

# 3. 推送到 GitHub 主分支
git push origin main
```

### 2. 自动化部署机制说明
* 当代码推送到 `main` 分支后，GitHub Actions 会自动触发 **`Deploy Honkit to GitHub Pages`** 任务：
  1. 在云端 Ubuntu 环境自动执行 `npm install` 和 `npx honkit build`；
  2. 将生成的 `_book/` 静态网页自动发布到仓库的 **`gh-pages`** 分支，并写入 `CNAME`（`trackform-manual.niekun.net`）。

### 3. 首次绑定自定义域名设置（仅需操作一次）
1. **GitHub 仓库设置**：
   打开 https://github.com/nie11kun/TrackForm-UserGuide/settings/pages ，在 **Build and deployment** 下：
   * **Source** 选择：**`Deploy from a branch`**
   * **Branch** 选择：**`gh-pages`** / **`/ (root)`**，点击 **Save**。
   * 勾选 **Enforce HTTPS**。
2. **DNS 域名解析设置**：
   在您的域名服务商（`niekun.net`）DNS 控制台中，添加一条 **CNAME 记录**：
   * **主机记录 (Host/Name)**：`trackform-manual`
   * **记录值 (Value/Target)**：`nie11kun.github.io`
   配置生效后，即可通过 **https://trackform-manual.niekun.net/** 访问在线手册。
