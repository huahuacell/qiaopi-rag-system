# 同学 A Git 协作指南：后端开发

## 1. 分支规则

- `main`：稳定主分支，不直接开发，不直接 push。
- `backend-a`：后端开发分支。
- `frontend-b`：前端开发分支。

同学 A 只改：

```text
backend/
docs/api_contract.md
```

不要主动改：

```text
frontend/
docs/test_cases.md
docs/demo_script.md
```

如果后端接口发生变化，需要同步更新 `docs/api_contract.md`，并通知前端同学。

---

## 2. 第一次进入项目

如果项目已经在本地，进入项目目录：

```bash
cd qiaopi-rag-system
```

创建并切换到后端分支：

```bash
git checkout -b backend-a
git push -u origin backend-a
```

确认当前分支：

```bash
git branch
```

必须看到：

```text
* backend-a
```

---

## 3. 每次开发前

```bash
git checkout backend-a
git pull origin backend-a
git pull origin main
```

确认不在 `main`：

```bash
git branch
```

看到 `* backend-a` 再开始写代码。

---

## 4. 本地运行后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

访问：

```text
http://localhost:8000/docs
http://localhost:8000/api/health
```

回到项目根目录：

```bash
cd ..
```

---

## 5. 提交到 backend-a

```bash
git status
git add .
git commit -m "Describe backend changes"
git push origin backend-a
```

注意：push 的是 `backend-a`，不是 `main`。

---

## 6. 什么时候创建 PR

代码确认可运行、接口测试通过，并且需要合并进 `main` 时，再创建 PR。

适合创建 PR 的情况：

1. Excel 入库、Dashboard、检索等阶段性后端功能完成后。
2. 一批 API 接口已经能正常返回 JSON 后。
3. `docs/api_contract.md` 已经同步更新后。
4. 需要把 `backend-a` 的成果合并进 `main` 给前端使用时。

PR 的作用：把 `backend-a` 中确认可用的代码合并到 `main`。

不是 PR 之后才能看到效果。PR 前也可以切到 `backend-a` 本地运行查看。

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
compare: backend-a
```

然后创建 PR。

### 方法 B：命令行创建，需要安装 GitHub CLI

```bash
gh pr create --base main --head backend-a --title "Implement backend APIs" --body "Implement backend APIs and update API contract."
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
backend/
docs/api_contract.md
```

不应该有：

```text
frontend/
docs/test_cases.md
docs/demo_script.md
```

如果误改了前端文件，先不要合并。

---

## 9. PR 合并后继续开发

PR 合并到 `main` 后：

```bash
git checkout backend-a
git pull origin backend-a
git pull origin main
```

然后继续在 `backend-a` 上开发。

---

## 10. 最重要的规则

1. 不直接改 `main`。
2. 不直接 push 到 `main`。
3. 开发前先确认当前分支是 `backend-a`。
4. 提交前先 `git status`。
5. PR 前检查 `Files changed`。
6. 不主动修改 `frontend/`、`docs/test_cases.md`、`docs/demo_script.md`。
7. 接口字段变化时，必须更新 `docs/api_contract.md`。
