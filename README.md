# 免费将 X 新帖转发到企业微信群

本项目使用 GitHub Actions 每 15 分钟检查一次 `@thsottiaux`。发现原创新帖后，自动发送到企业微信群机器人。

## 使用前须知

- 不需要购买 X API，也不需要服务器。
- 免费方案依赖第三方 RSS 镜像，可能因 X 限制而临时失效、延迟或漏消息。
- GitHub 的定时任务不是严格准点运行，繁忙时可能延迟数分钟。
- 首次运行只记录当前帖子，不会把历史内容刷进群。
- 默认忽略常见格式的回复和转帖；不同 RSS 源的格式可能导致过滤不完全。

## 一、创建 GitHub 仓库

1. 登录 GitHub，点击 **New repository**。
2. 建议创建公开仓库，以免消耗私有仓库的 Actions 免费分钟数。
3. 把本目录里的所有文件上传到仓库根目录。必须包括 `.github/workflows/x-to-wecom.yml`。

如果网页上传时看不到 `.github`，可以在仓库网页中依次创建目录和文件，或者使用 GitHub Desktop 上传整个目录。

## 二、创建企业微信群机器人

1. 在企业微信电脑版打开接收通知的群。
2. 打开群设置，选择 **群机器人 → 添加群机器人**。
3. 创建机器人并复制 Webhook 地址。

Webhook 类似：

```text
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx
```

不要把 Webhook 写进代码、README、Issue 或聊天记录。

## 三、保存 Webhook 密钥

1. 进入 GitHub 仓库的 **Settings**。
2. 进入 **Secrets and variables → Actions**。
3. 点击 **New repository secret**。
4. Name 填 `WECOM_WEBHOOK`。
5. Secret 填完整的企业微信 Webhook 地址并保存。

## 四、首次运行

1. 打开仓库的 **Actions** 页面。
2. 选择左侧的 **X to WeCom**。
3. 点击 **Run workflow**。
4. 等待任务显示绿色对勾。

第一次只建立去重记录，不发送历史帖子。任务会自动提交 `state/seen.json`。此后发现新帖才会推送。

## 五、测试企业微信通知

首次运行成功后，可以等待该账号发布新帖。若想立即验证 Webhook，可在自己的电脑运行：

```bash
curl '你的企业微信Webhook地址' \
  -H 'Content-Type: application/json' \
  -d '{"msgtype":"text","text":{"content":"X 转发机器人测试成功"}}'
```

请勿把替换了真实 Webhook 的命令截图或公开分享。

## 免费 RSS 源全部失效怎么办

项目默认依次尝试三个公共源。如果默认源均不可用，可以添加自己的源：

1. 进入 **Settings → Secrets and variables → Actions**。
2. 新建名为 `FEED_URLS` 的 Secret。
3. 填入一个或多个 RSS 地址，多个地址用英文逗号分隔。

RSS 内容中的帖子链接需要包含 `/status/数字ID`。程序会按填写顺序尝试，找到可用源后停止。

## 修改账号或检查频率

修改 `.github/workflows/x-to-wecom.yml`：

```yaml
X_USERNAME: thsottiaux
```

定时配置当前为：

```yaml
- cron: "7,22,37,52 * * * *"
```

表示每小时的第 7、22、37、52 分钟检查。GitHub 定时表达式使用 UTC，但这个任务不依赖时区。

## 常见问题

### Actions 显示红色错误

打开失败任务的 **Check for new posts** 步骤查看原因：

- `所有免费 RSS 源均不可用`：公共 RSS 镜像暂时不可用，可稍后重试或设置 `FEED_URLS`。
- `未设置 WECOM_WEBHOOK`：检查 Secret 名称是否完全一致。
- `企业微信返回错误`：机器人可能已被移出群，或 Webhook 已失效。

### 收到重复消息

确认 `state/seen.json` 已被 Actions 自动提交，并在仓库 **Settings → Actions → General** 中允许工作流具有读写权限。如果组织策略禁止写入仓库，需要手动调整权限。

### 很久没有自动运行

先在 Actions 页面手动执行一次。如果 GitHub 因仓库长期无活动而暂停计划任务，手动运行或提交一次代码后可恢复。

## 本地测试

项目只使用 Python 标准库：

```bash
python -m unittest discover -s tests -v
```
