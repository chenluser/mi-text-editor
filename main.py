# -*- coding: utf-8 -*-
"""最小验证版: 只显示一行文字。用于确认 Kivy 能否在本机启动。"""
from kivy.app import App
from kivy.uix.label import Label


class TextEditorApp(App):
    def build(self):
        return Label(text='MIN OK - Kivy started', font_size='24sp')


if __name__ == '__main__':
    TextEditorApp().run()
