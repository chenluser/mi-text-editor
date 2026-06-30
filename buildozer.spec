[app]
title = 小米文本编辑器
package.name = mitexteditor
package.domain = org.chenluser
source.dir = .
source.include_exts = py,png,jpg,ttf,ttc,otf
source.exclude_dirs = tests,bin,.buildozer,__pycache__
version = 1.0.0

# 对齐漫画查看器验证过的版本组合 (kivy 2.3.1 + ndk 25b + sdk 33 + 单架构)。
# 额外钉 Python 3.11: p4a master 默认已升到 3.14, Kivy 不兼容会编译报错。
requirements = python3==3.11.9,kivy==2.3.1,android,pyjnius

orientation = all
fullscreen = 0

# SAF / DocumentFile 需要 androidx 支持库
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1
android.enable_androidx = True

# 权限: SAF 本身不需要存储权限
android.permissions = INTERNET

# SDK / NDK (对齐漫画查看器成功配置)
android.api = 33
android.minapi = 24
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
