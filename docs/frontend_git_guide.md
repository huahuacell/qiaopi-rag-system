# 同学 B Git 协作指南：前端开发

## 1. 分支规则

- `main`：稳定主分支，不直接开发，不直接 push。
- `frontend-b`：前端开发分支。
- `backend-a`：后端开发分支。

同学 B 只改：

```text
frontend/
docs/test_cases.md
docs/demo_script.md
```

不要主动改：

```text
backend/
docs/api_contract.md
```

如果前端需要新增接口或字段，先联系后端同学修改后端接口和 `docs/api_contract.md`。

---

## 2. 第一次下载项目

```bash
git clone https://github.com/huahuacell/qiaopi-rag-system.git
cd qiaopi-rag-system
git checkout -b frontend-b
git push -u origin frontend-b
```

确认当前分支：

```bash
git branch
```

必须看到：

```text
* frontend-b
```

---

## 3. 每次开发前

```bash
git checkout frontend-b
git pull origin frontend-b
git pull origin main
```

确认不在 `main`：

```bash
git branch
```

看到 `* frontend-b` 再开始写代码。

---

## 4. 本地运行前端

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

回到项目根目录：

```bash
cd ..
```

---

## 5. 提交到 frontend-b

```bash
git status
git add .
git commit -m "Describe frontend changes"
git push origin frontend-b
```

注意：push 的是 `frontend-b`，不是 `main`。

---

## 6. 什么时候创建 PR

代码确认可运行、页面效果确认没问题，并且需要合并进 `main` 时，再创建 PR。

适合创建 PR 的情况：

1. 一个页面或一组页面完成后。
2. 一批后端接口接好并确认能正常展示后。
3. 准备阶段性整合、截图、演示时。
4. 需要把 `frontend-b` 的成果合并进 `main` 给全组使用时。

PR 的作用：把 `frontend-b` 中确认可用的代码合并到 `main`。

不是 PR 之后才能看到效果。PR 前也可以切到 `frontend-b` 本地运行查看。

---

## 7. 创建 PR

### 方法 A：GitHub 网页创建，推荐

push 后打开 GitHub 仓库页面，点击：

```text
Compare & pull request
```

确认：

```text
base: main
compare: frontend-b
```

然后创建 PR。

### 方法 B：命令行创建，需要安装 GitHub CLI

```bash
gh pr create --base main --head frontend-b --title "Refine frontend views" --body "Refine frontend pages and update demo docs."
```

查看 PR 状态：

```bash
gh pr status
```

---

## 8. PR 前检查

PR 页面里检查 `Files changed`。

正常可以有：

```text
frontend/
docs/test_cases.md
docs/demo_script.md
```

不应该有：

```text
backend/
docs/api_contract.md
```

如果误改了后端文件，先不要合并。

---

## 9. PR 合并后继续开发

PR 合并到 `main` 后：

```bash
git checkout frontend-b
git pull origin frontend-b
git pull origin main
```

然后继续在 `frontend-b` 上开发。

---

## 10. 最重要的规则

1. 不直接改 `main`。
2. 不直接 push 到 `main`。
3. 开发前先确认当前分支是 `frontend-b`。
4. 提交前先 `git status`。
5. PR 前检查 `Files changed`。
6. 不主动修改 `backend/` 和 `docs/api_contract.md`。
