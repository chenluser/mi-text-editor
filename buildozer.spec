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

# 锁定 p4a 到正式发布版 v2024.01.21: python3 recipe = 3.11.5 (避开 master 的 3.14),
# 推荐 NDK 正好是 25b (与下方 android.ndk 一致), 是经过发布测试的稳定版,
# 不像中间 commit 会带 pyjnius 隔离构建 setuptools.build_meta 不兼容问题。
p4a.url = https://github.com/kivy/python-for-android.git
p4a.branch = v2024.01.21

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
