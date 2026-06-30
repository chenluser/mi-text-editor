[app]
title = 小米文本编辑器
package.name = mitexteditor
package.domain = org.chenluser
source.dir = .
source.include_exts = py,png,jpg,ttf,ttc,otf
source.exclude_dirs = tests,bin,.buildozer,__pycache__
version = 1.0.0

# 对齐漫画查看器验证过的版本组合 (kivy 2.3.1 + ndk 25b + sdk 33 + 单架构)。
# 不显式钉 python3 版本, 由 p4a 自带 recipe 决定 (下方锁定的 commit 默认 3.11.13)。
requirements = python3,kivy==2.3.1,android,pyjnius

# 锁定 p4a 到 "Update to Python 3.14" 之前的 commit (2025-10-08, 默认 Python 3.11.13)。
# p4a master 现在强制 Python 3.14, 而 Kivy 2.3.1 的 C 代码不兼容 3.14 (texture.c 编译报错)。
p4a.url = https://github.com/kivy/python-for-android.git
p4a.commit = 6b66944a2

orientation = all
fullscreen = 0

# SAF / DocumentFile 需要 androidx 支持库
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1
android.enable_androidx = True

# 权限: SAF 本身不需要存储权限
android.permissions = INTERNET

# SDK / NDK (对齐漫画查看器成功配置)
android.api = 33
# minapi 必须 >= 26: Python 3.11.13 的 grpmodule.c 用到 setgrent/getgrent/endgrent,
# 这些在 Android bionic libc 直到 API 26 才提供, 否则编译报 implicit declaration 错误。
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
# 单架构, 覆盖 99% 现役机型, 构建更快
android.archs = arm64-v8a
android.allow_backup = True

entrypoint = main.py
android.release_artifact = apk
android.debug_artifact = apk

log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
build_dir = ./.buildozer
bin_dir = ./bin
