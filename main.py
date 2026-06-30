# -*- coding: utf-8 -*-
"""
小米文本编辑器 (Kivy + SAF)
- Android: 通过存储访问框架 (SAF) 读写 /Android/data 等目录, 增删改查文件
- 桌面: 退化为普通文件系统浏览, 方便测试 UI
"""
import os
import json
import traceback

from kivy.app import App
from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.text import LabelBase
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition

IS_ANDROID = (platform == 'android')

# ---------------- 中文字体 ----------------
FONT = 'Roboto'
def _register_font():
    candidates = []
    if IS_ANDROID:
        candidates = [
            '/system/fonts/NotoSansCJK-Regular.ttc',
            '/system/fonts/NotoSansSC-Regular.otf',
            '/system/fonts/DroidSansFallback.ttf',
        ]
    else:
        win = os.environ.get('WINDIR', 'C:\\Windows')
        candidates = [os.path.join(win, 'Fonts', f) for f in
                      ('msyh.ttc', 'simhei.ttf', 'simsun.ttc')]
    for f in candidates:
        if os.path.exists(f):
            try:
                LabelBase.register('Roboto', f, f, f, f)
                return
            except Exception:
                pass
_register_font()

# ================================================================
# 存储后端抽象层
#   Backend 提供统一接口:
#     list(node)            -> [Entry, ...]   列目录
#     read(node)            -> str            读文件文本
#     write(node, text)     -> bool           写文件
#     create(parent, name)  -> Entry          新建文件
#     mkdir(parent, name)   -> Entry          新建文件夹
#     delete(node)          -> bool           删除
#     rename(node, name)    -> Entry          重命名
#   node/Entry 是一个轻量包装, 在桌面是路径字符串, 在 Android 是 DocumentFile 的 URI
# ================================================================

class Entry(object):
    """目录项: name 显示名, is_dir 是否目录, ref 后端内部引用 (路径 或 DocumentFile)"""
    __slots__ = ('name', 'is_dir', 'ref', 'size')
    def __init__(self, name, is_dir, ref, size=0):
        self.name = name
        self.is_dir = is_dir
        self.ref = ref
        self.size = size


# ---------------- 桌面后端 ----------------
class DesktopBackend(object):
    name = 'desktop'

    def root_label(self):
        return os.path.abspath(self.root) if hasattr(self, 'root') else '/'

    def __init__(self, root=None):
        self.root = root or os.path.expanduser('~')

    def root_entry(self):
        p = os.path.abspath(self.root)
        return Entry(os.path.basename(p) or p, True, p)

    def list(self, node):
        out = []
        try:
            for nm in sorted(os.listdir(node.ref)):
                full = os.path.join(node.ref, nm)
                isd = os.path.isdir(full)
                sz = 0
                try:
                    sz = 0 if isd else os.path.getsize(full)
                except OSError:
                    pass
                out.append(Entry(nm, isd, full, sz))
        except OSError as e:
            raise IOError(str(e))
        out.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return out

    def read(self, node):
        with open(node.ref, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    def write(self, node, text):
        tmp = node.ref + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, node.ref)
        return True

    def create(self, parent, name):
        full = os.path.join(parent.ref, name)
        open(full, 'a', encoding='utf-8').close()
        return Entry(name, False, full)

    def mkdir(self, parent, name):
        full = os.path.join(parent.ref, name)
        os.makedirs(full, exist_ok=True)
        return Entry(name, True, full)

    def delete(self, node):
        if node.is_dir:
            import shutil
            shutil.rmtree(node.ref)
        else:
            os.remove(node.ref)
        return True

    def rename(self, node, new_name):
        newp = os.path.join(os.path.dirname(node.ref), new_name)
        os.rename(node.ref, newp)
        return Entry(new_name, node.is_dir, newp, node.size)


# ---------------- Android SAF 后端 ----------------
# 通过 DocumentFile (tree URI) 访问授权目录, ContentResolver 读写流。
# ref 存的是 DocumentFile 的 Java 对象。
class AndroidSAFBackend(object):
    name = 'saf'

    def __init__(self):
        from jnius import autoclass
        self.autoclass = autoclass
        self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
        self.DocumentFile = autoclass('androidx.documentfile.provider.DocumentFile')
        self.Uri = autoclass('android.net.Uri')
        self.activity = self.PythonActivity.mActivity
        self.resolver = self.activity.getContentResolver()
        self._root_doc = None      # DocumentFile (tree)
        self._root_name = '(未授权)'

    # 由 SAF 选择器回调设置的 tree uri 字符串
    def set_root_uri(self, uri_str):
        uri = self.Uri.parse(uri_str)
        # 持久化授权, 重启后仍可访问
        try:
            FLAG = (self.autoclass('android.content.Intent').FLAG_GRANT_READ_URI_PERMISSION |
                    self.autoclass('android.content.Intent').FLAG_GRANT_WRITE_URI_PERMISSION)
            self.resolver.takePersistableUriPermission(uri, FLAG)
        except Exception:
            pass
        self._root_doc = self.DocumentFile.fromTreeUri(self.activity, uri)
        try:
            self._root_name = self._root_doc.getName() or 'root'
        except Exception:
            self._root_name = 'root'

    def has_root(self):
        return self._root_doc is not None

    def root_label(self):
        return self._root_name

    def root_entry(self):
        return Entry(self._root_name, True, self._root_doc)

    def _wrap(self, doc):
        try:
            nm = doc.getName() or '?'
        except Exception:
            nm = '?'
        isd = doc.isDirectory()
        sz = 0
        try:
            sz = 0 if isd else doc.length()
        except Exception:
            pass
        return Entry(nm, isd, doc, sz)

    def list(self, node):
        out = []
        files = node.ref.listFiles()   # DocumentFile[]
        for i in range(len(files)):
            out.append(self._wrap(files[i]))
        out.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return out

    def read(self, node):
        # 用 ByteArrayOutputStream 汇总, byte[] 缓冲批量读
        InputStream = self.resolver.openInputStream(node.ref.getUri())
        ByteArrayOutputStream = self.autoclass('java.io.ByteArrayOutputStream')
        baos = ByteArrayOutputStream()
        try:
            jbuf = self._new_byte_array(65536)
            n = InputStream.read(jbuf)
            while n != -1:
                baos.write(jbuf, 0, n)
                n = InputStream.read(jbuf)
            raw = baos.toByteArray()           # java signed byte[]
            py = bytes((x & 0xFF) for x in raw) # 转无符号 python bytes
            return py.decode('utf-8', errors='replace')
        finally:
            try:
                InputStream.close()
            except Exception:
                pass

    def _new_byte_array(self, size):
        """创建一个 java byte[]。pyjnius 可接受 python bytearray 作为 byte[] 参数,
        但 read(byte[]) 需要一个可写的 java 数组, 用反射创建。"""
        ArrayClass = self.autoclass('java.lang.reflect.Array')
        ByteType = self.autoclass('java.lang.Byte').TYPE
        return ArrayClass.newInstance(ByteType, size)

    def write(self, node, text):
        data = text.encode('utf-8')
        out = self.resolver.openOutputStream(node.ref.getUri(), 'wt')  # 截断写
        try:
            # pyjnius 支持把 python bytes/bytearray 直接传给 byte[] 参数
            out.write(bytearray(data))
            out.flush()
        finally:
            try:
                out.close()
            except Exception:
                pass
        return True

    def create(self, parent, name):
        mime = 'text/plain'
        doc = parent.ref.createFile(mime, name)
        if doc is None:
            raise IOError('创建文件失败 (可能已存在或无权限)')
        return self._wrap(doc)

    def mkdir(self, parent, name):
        doc = parent.ref.createDirectory(name)
        if doc is None:
            raise IOError('创建文件夹失败')
        return self._wrap(doc)

    def delete(self, node):
        ok = node.ref.delete()
        if not ok:
            raise IOError('删除失败')
        return True

    def rename(self, node, new_name):
        ok = node.ref.renameTo(new_name)
        if not ok:
            raise IOError('重命名失败')
        return self._wrap(node.ref)


# ================================================================
# SAF 目录选择器 (Android)
#   通过 Intent.ACTION_OPEN_DOCUMENT_TREE 弹出系统选择器,
#   EXTRA_INITIAL_URI 尝试深链到 Android/data。
#   结果在 on_activity_result 回调里拿到 tree uri。
# ================================================================
REQUEST_OPEN_TREE = 0xA1

# data 目录的深链 URI (部分小米/HyperOS 机型有效, 失败则退化到选择器默认位置)
INITIAL_DATA_URI = (
    'content://com.android.externalstorage.documents/document/'
    'primary%3AAndroid%2Fdata'
)


class SAFChooser(object):
    def __init__(self, on_result):
        from jnius import autoclass
        self.autoclass = autoclass
        self.on_result = on_result          # 回调: on_result(uri_str or None)
        self.Intent = autoclass('android.content.Intent')
        self.Uri = autoclass('android.net.Uri')
        self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
        from android import activity         # python-for-android 提供
        self._android_activity = activity
        activity.bind(on_activity_result=self._on_activity_result)

    def open(self, deep_link_data=True):
        intent = self.Intent(self.Intent.ACTION_OPEN_DOCUMENT_TREE)
        intent.addFlags(
            self.Intent.FLAG_GRANT_READ_URI_PERMISSION |
            self.Intent.FLAG_GRANT_WRITE_URI_PERMISSION |
            self.Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
        )
        if deep_link_data:
            try:
                init = self.Uri.parse(INITIAL_DATA_URI)
                # EXTRA_INITIAL_URI 在 API 26+ 可用
                intent.putExtra('android.provider.extra.INITIAL_URI', init)
            except Exception:
                pass
        act = self.PythonActivity.mActivity
        act.startActivityForResult(intent, REQUEST_OPEN_TREE)

    def _on_activity_result(self, requestCode, resultCode, intent):
        if requestCode != REQUEST_OPEN_TREE:
            return
        try:
            RESULT_OK = -1
            if resultCode != RESULT_OK or intent is None:
                Clock.schedule_once(lambda dt: self.on_result(None), 0)
                return
            uri = intent.getData()
            uri_str = uri.toString()
            Clock.schedule_once(lambda dt: self.on_result(uri_str), 0)
        except Exception:
            Clock.schedule_once(lambda dt: self.on_result(None), 0)


# ================================================================
# 配置持久化 (记住上次授权的目录 uri)
# ================================================================
def _config_path():
    if IS_ANDROID:
        try:
            from android.storage import app_storage_path
            base = app_storage_path()
        except Exception:
            base = os.path.expanduser('~')
    else:
        base = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
                            'mi_text_editor')
    try:
        os.makedirs(base, exist_ok=True)
    except OSError:
        pass
    return os.path.join(base, 'config.json')


def load_config():
    try:
        with open(_config_path(), 'r', encoding='utf-8') as f:
            d = json.load(f)
            if isinstance(d, dict):
                return d
    except Exception:
        pass
    return {}


def save_config(cfg):
    try:
        p = _config_path()
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False)
        os.replace(tmp, p)
    except Exception:
        pass


# ================================================================
# UI 辅助
# ================================================================
def B(text, on_press=None, **kw):
    b = Button(text=text, font_name=FONT, font_size=dp(16), **kw)
    if on_press:
        b.bind(on_release=on_press)
    return b


def toast(msg):
    if IS_ANDROID:
        try:
            from jnius import autoclass, cast
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Toast = autoclass('android.widget.Toast')
            String = autoclass('java.lang.String')
            activity = PythonActivity.mActivity
            def _show(dt):
                Toast.makeText(activity, cast('java.lang.CharSequence',
                               String(msg)), Toast.LENGTH_SHORT).show()
            Clock.schedule_once(_show, 0)
            return
        except Exception:
            pass
    print('[toast]', msg)


def confirm_popup(title, message, on_yes):
    box = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(12))
    box.add_widget(Label(text=message, font_name=FONT, font_size=dp(15)))
    row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
    pop = Popup(title=title, content=box, size_hint=(0.85, 0.4),
                title_font=FONT)
    def yes(*_):
        pop.dismiss()
        on_yes()
    row.add_widget(B('取消', lambda *_: pop.dismiss()))
    row.add_widget(B('确定', yes, background_color=(0.8, 0.3, 0.3, 1)))
    box.add_widget(row)
    pop.open()


def input_popup(title, on_ok, default=''):
    box = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(12))
    ti = TextInput(text=default, font_name=FONT, multiline=False,
                   size_hint_y=None, height=dp(48), font_size=dp(16))
    box.add_widget(ti)
    row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
    pop = Popup(title=title, content=box, size_hint=(0.85, 0.4), title_font=FONT)
    def ok(*_):
        v = ti.text.strip()
        pop.dismiss()
        if v:
            on_ok(v)
    row.add_widget(B('取消', lambda *_: pop.dismiss()))
    row.add_widget(B('确定', ok, background_color=(0.3, 0.6, 0.8, 1)))
    box.add_widget(row)
    pop.open()
    Clock.schedule_once(lambda dt: setattr(ti, 'focus', True), 0.2)


# ================================================================
# 文件浏览屏
# ================================================================
class BrowseScreen(Screen):
    def __init__(self, app, **kw):
        super(BrowseScreen, self).__init__(**kw)
        self.app = app
        self.stack = []        # 导航栈: [Entry(dir), ...] 根在栈底
        root = BoxLayout(orientation='vertical')

        # 顶栏
        top = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(4),
                        padding=[dp(6), dp(4)])
        self.btn_up = B('↑上级', self._go_up, size_hint_x=None, width=dp(78))
        self.path_lbl = Label(text='', font_name=FONT, font_size=dp(13),
                              halign='left', valign='middle', shorten=True,
                              shorten_from='left')
        self.path_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        top.add_widget(self.btn_up)
        top.add_widget(self.path_lbl)
        root.add_widget(top)

        # 文件列表
        self.scroll = ScrollView()
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2),
                               padding=[dp(6), dp(4)])
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        root.add_widget(self.scroll)

        # 底栏
        bar = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(4),
                        padding=[dp(6), dp(4)])
        bar.add_widget(B('选目录', lambda *_: self.app.pick_directory()))
        bar.add_widget(B('新建文件', lambda *_: self._new_file()))
        bar.add_widget(B('新建夹', lambda *_: self._new_dir()))
        bar.add_widget(B('刷新', lambda *_: self.refresh()))
        root.add_widget(bar)

        self.add_widget(root)

    def open_root(self):
        be = self.app.backend
        self.stack = [be.root_entry()]
        self.refresh()

    def _go_up(self, *_):
        if len(self.stack) > 1:
            self.stack.pop()
            self.refresh()
        else:
            toast('已在根目录')

    def _cur(self):
        return self.stack[-1] if self.stack else None

    def refresh(self):
        self.grid.clear_widgets()
        cur = self._cur()
        if cur is None:
            self.path_lbl.text = '未选择目录'
            return
        # 路径面包屑
        self.path_lbl.text = ' / '.join(e.name for e in self.stack)
        try:
            entries = self.app.backend.list(cur)
        except Exception as e:
            self.grid.add_widget(Label(text='无法读取目录:\n%s' % e,
                                       font_name=FONT, size_hint_y=None,
                                       height=dp(80)))
            return
        if not entries:
            self.grid.add_widget(Label(text='(空目录)', font_name=FONT,
                                       size_hint_y=None, height=dp(60)))
        for ent in entries:
            self.grid.add_widget(self._make_row(ent))

    def _make_row(self, ent):
        row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(4))
        icon = '📁' if ent.is_dir else '📄'
        szs = '' if ent.is_dir else _fmt_size(ent.size)
        label = '%s %s' % (icon, ent.name)
        main = B(label, halign='left')
        main.text_size = (main.width, None)
        main.bind(size=lambda w, s: setattr(w, 'text_size', (s[0] - dp(10), None)))
        main.halign = 'left'
        main.valign = 'middle'
        main.background_color = (0.18, 0.18, 0.22, 1) if ent.is_dir else (0.13, 0.13, 0.16, 1)
        main.bind(on_release=lambda *_: self._on_tap(ent))
        row.add_widget(main)
        if szs:
            row.add_widget(Label(text=szs, font_name=FONT, font_size=dp(11),
                                 size_hint_x=None, width=dp(70),
                                 color=(0.6, 0.6, 0.6, 1)))
        menu = B('⋮', lambda *_: self._row_menu(ent), size_hint_x=None,
                 width=dp(44))
        row.add_widget(menu)
        return row

    def _on_tap(self, ent):
        if ent.is_dir:
            self.stack.append(ent)
            self.refresh()
        else:
            self.app.open_editor(ent)

    def _row_menu(self, ent):
        box = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(10))
        pop = Popup(title=ent.name, content=box, size_hint=(0.8, 0.55),
                    title_font=FONT)
        def act(fn):
            def _(*_a):
                pop.dismiss()
                fn()
            return _
        if not ent.is_dir:
            box.add_widget(B('打开编辑', act(lambda: self.app.open_editor(ent))))
        box.add_widget(B('重命名', act(lambda: self._rename(ent))))
        box.add_widget(B('删除', act(lambda: self._delete(ent)),
                        background_color=(0.8, 0.3, 0.3, 1)))
        box.add_widget(B('关闭', lambda *_: pop.dismiss()))
        pop.open()

    def _new_file(self):
        cur = self._cur()
        if cur is None:
            return
        def make(name):
            try:
                self.app.backend.create(cur, name)
                self.refresh()
                toast('已新建 ' + name)
            except Exception as e:
                toast('失败: %s' % e)
        input_popup('新建文件名', make, default='新文件.txt')

    def _new_dir(self):
        cur = self._cur()
        if cur is None:
            return
        def make(name):
            try:
                self.app.backend.mkdir(cur, name)
                self.refresh()
                toast('已新建文件夹')
            except Exception as e:
                toast('失败: %s' % e)
        input_popup('新建文件夹名', make, default='新文件夹')

    def _rename(self, ent):
        def do(name):
            try:
                self.app.backend.rename(ent, name)
                self.refresh()
                toast('已重命名')
            except Exception as e:
                toast('失败: %s' % e)
        input_popup('重命名', do, default=ent.name)

    def _delete(self, ent):
        def do():
            try:
                self.app.backend.delete(ent)
                self.refresh()
                toast('已删除')
            except Exception as e:
                toast('失败: %s' % e)
        confirm_popup('删除确认', '确定删除 "%s" ?%s' % (
            ent.name, '\n(文件夹将连同内容一起删除)' if ent.is_dir else ''), do)


def _fmt_size(n):
    for unit in ('B', 'K', 'M', 'G'):
        if n < 1024:
            return '%d%s' % (n, unit) if unit == 'B' else '%.1f%s' % (n, unit)
        n /= 1024.0
    return '%.1fT' % n


# ================================================================
# 编辑屏
# ================================================================
class EditScreen(Screen):
    def __init__(self, app, **kw):
        super(EditScreen, self).__init__(**kw)
        self.app = app
        self.entry = None
        self._orig = ''
        root = BoxLayout(orientation='vertical')

        top = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(4),
                        padding=[dp(6), dp(4)])
        top.add_widget(B('← 返回', lambda *_: self._back(), size_hint_x=None,
                         width=dp(90)))
        self.title_lbl = Label(text='', font_name=FONT, font_size=dp(14),
                               shorten=True, shorten_from='left')
        self.title_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        top.add_widget(self.title_lbl)
        top.add_widget(B('保存', lambda *_: self.save(), size_hint_x=None,
                         width=dp(80), background_color=(0.3, 0.6, 0.8, 1)))
        root.add_widget(top)

        self.editor = TextInput(text='', font_name=FONT, font_size=dp(16),
                                 multiline=True, do_wrap=True)
        root.add_widget(self.editor)

        info = BoxLayout(size_hint_y=None, height=dp(30), padding=[dp(8), 0])
        self.status = Label(text='', font_name=FONT, font_size=dp(11),
                            halign='left', valign='middle',
                            color=(0.6, 0.6, 0.6, 1))
        self.status.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info.add_widget(self.status)
        root.add_widget(info)

        self.add_widget(root)

    def load(self, entry):
        self.entry = entry
        self.title_lbl.text = entry.name
        try:
            txt = self.app.backend.read(entry)
        except Exception as e:
            txt = ''
            toast('读取失败: %s' % e)
        self._orig = txt
        self.editor.text = txt
        self.status.text = '%d 字符' % len(txt)

    def save(self):
        if self.entry is None:
            return
        try:
            self.app.backend.write(self.entry, self.editor.text)
            self._orig = self.editor.text
            self.status.text = '已保存 · %d 字符' % len(self.editor.text)
            toast('已保存')
        except Exception as e:
            toast('保存失败: %s' % e)

    def _back(self):
        if self.editor.text != self._orig:
            confirm_popup('未保存', '有改动未保存, 确定离开?',
                          lambda: self.app.go_browse())
        else:
            self.app.go_browse()


# ================================================================
# App
# ================================================================
class TextEditorApp(App):
    def build(self):
        self.title = '小米文本编辑器'
        self.cfg = load_config()
        self.backend = None
        self._chooser = None

        self.sm = ScreenManager(transition=NoTransition())
        self.browse = BrowseScreen(self, name='browse')
        self.edit = EditScreen(self, name='edit')
        self.sm.add_widget(self.browse)
        self.sm.add_widget(self.edit)

        Clock.schedule_once(lambda dt: self._init_backend(), 0.3)
        return self.sm

    def _init_backend(self):
        if IS_ANDROID:
            self.backend = AndroidSAFBackend()
            saved = self.cfg.get('tree_uri')
            if saved:
                try:
                    self.backend.set_root_uri(saved)
                    if self.backend.has_root():
                        self.browse.open_root()
                        return
                except Exception:
                    pass
            self._prompt_pick()
        else:
            # 桌面: 默认从用户目录开始, 方便测试
            self.backend = DesktopBackend(self.cfg.get('desktop_root'))
            self.browse.open_root()

    def _prompt_pick(self):
        box = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(14))
        box.add_widget(Label(
            text='需要授权一个目录才能读写文件。\n\n'
                 '点击"选择目录"后, 在系统选择器里\n'
                 '导航到 Android/data 或任意目录,\n'
                 '然后点底部的"使用此文件夹"并允许。',
            font_name=FONT, font_size=dp(14)))
        pop = Popup(title='授权目录', content=box, size_hint=(0.9, 0.5),
                    title_font=FONT, auto_dismiss=False)
        def go(*_):
            pop.dismiss()
            self.pick_directory()
        box.add_widget(B('选择目录', go, size_hint_y=None, height=dp(50),
                         background_color=(0.3, 0.6, 0.8, 1)))
        pop.open()

    def pick_directory(self):
        if not IS_ANDROID:
            toast('桌面模式: 浏览本地文件系统')
            return
        if self._chooser is None:
            self._chooser = SAFChooser(self._on_dir_picked)
        self._chooser.open(deep_link_data=True)

    def _on_dir_picked(self, uri_str):
        if not uri_str:
            toast('未授权')
            return
        try:
            self.backend.set_root_uri(uri_str)
            self.cfg['tree_uri'] = uri_str
            save_config(self.cfg)
            self.browse.open_root()
            toast('已授权: ' + self.backend.root_label())
        except Exception as e:
            toast('授权失败: %s' % e)

    def open_editor(self, entry):
        self.edit.load(entry)
        self.sm.current = 'edit'

    def go_browse(self):
        self.sm.current = 'browse'
        self.browse.refresh()

    def on_pause(self):
        return True


if __name__ == '__main__':
    try:
        TextEditorApp().run()
    except Exception:
        traceback.print_exc()
