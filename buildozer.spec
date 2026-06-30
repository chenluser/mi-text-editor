[app]
title = 小米文本编辑器
package.name = mitexteditor
package.domain = org.chenluser
source.dir = .
source.include_exts = py,png,jpg,ttf,ttc,otf
version = 1.0.0
requirements = python3,kivy==2.3.0,android,pyjnius
orientation = all
fullscreen = 0

# SAF / DocumentFile 需要 androidx 支持库
android.gradle_dependencies = androidx.documentfile:documentfile:1.0.1
android.enable_androidx = True

# 权限: SAF 本身不需要存储权限, 但保留基础项
android.permissions = INTERNET

# SDK / API
android.api = 33
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

# 入口
android.entrypoint = org.kivy.android.PythonActivity

[buildozer]
log_level = 2
warn_on_root = 0
