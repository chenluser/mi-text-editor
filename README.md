# 小米文本编辑器 (Mi Text Editor)

适配小米 / HyperOS 手机的文本编辑器,基于 Kivy + SAF(存储访问框架),可对文件进行**增删改查**,并能读取 `Android/data` 目录内的文本文件。

## 功能

- 浏览目录,进入子文件夹,返回上级
- 打开文本文件查看 / 编辑 / 保存(UTF-8)
- 新建文件、新建文件夹
- 重命名、删除(文件 / 文件夹)
- 记住上次授权的目录,重启免再授权

## 关于 Android/data 访问(重要)

从 Android 11 起,`/Android/data/` 无法用普通文件路径直接访问,即使有「所有文件访问权限」也不行。本应用使用 **SAF(存储访问框架)**:

1. 首次启动弹出授权提示 → 点「选择目录」
2. 系统文件选择器会尝试**自动定位到 `Android/data`**(深链)
3. 在选择器里点底部的「使用此文件夹」并「允许」
4. 之后即可读写该目录及其子目录

> 注意:Google 在新系统上逐步收紧对 `Android/data` 根目录的 SAF 授权。若系统拦截,可退一步授权某个具体的 App 子目录(如 `Android/data/com.xxx.app`),或选择 `/sdcard` 等其他目录。授权一次长期有效。

## 构建(GitHub Actions 云构建)

本机无需 Linux / Docker:

1. 把本目录推到 GitHub 仓库的 `main` 分支
2. Actions 自动运行(首次 15-25 分钟,缓存后 8-15 分钟)
3. 运行结束 → 该 run → Artifacts → 下载 `MiTextEditor-APK-build<N>`
4. 解压得 `MiTextEditor-<N>.apk`,传手机安装

每次改代码记得把 `buildozer.spec` 的 `version` +1,否则同版本号 APK 装不上去。

## 桌面测试

```bash
python main.py
```

桌面模式下退化为普通文件系统浏览(从用户主目录开始),方便验证 UI。

## 文件

| 文件 | 说明 |
|------|------|
| `main.py` | 全部源码:存储后端抽象 + SAF + UI |
| `buildozer.spec` | 构建配置(含 androidx.documentfile 依赖) |
| `.github/workflows/android.yml` | CI 构建 + 签名 |
