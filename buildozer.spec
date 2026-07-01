[app]
title = 小米文本编辑器
package.name = mitexteditor
package.domain = org.chenluser
source.dir = .
source.include_exts = py,png,jpg,ttf,ttc,otf
source.exclude_dirs = tests,bin,.buildozer,__pycache__
version = 1.0.4

# 完全对齐漫画查看器 2026-05-20 成功配置: 裸用 p4a master (不锁版本!),
# Kivy 2.3.1 + Python 3.14 + NDK 25b + minAPI 24 已验证可在小米手机运行。
# 之前锁 p4a v2024.01.21 是帮倒忙 (引入老版本不兼容 + pyjnius setuptools 问题)。
requirements = python3,kivy==2.3.1,pillow,pyjnius,android,plyer

orientation = all
fullscreen = 0

# SAF / DocumentFile 需要 androidx 支持库
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1
android.enable_androidx = True

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
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
