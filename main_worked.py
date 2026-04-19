# FINAL VERSION: PyQt6 Audio Player
# - Clean UI
# - Async waveform + DB cache
# - Tags (create, assign, sync)
# - Search + tag filter

import sys, json
from pathlib import Path
import numpy as np

from PyQt6.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from sqlalchemy import create_engine, Column, Integer, String, Table, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from pydub import AudioSegment

# ================= MODELS =================
Base = declarative_base()

track_tag = Table('track_tag', Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id')),
    Column('tag_id', Integer, ForeignKey('tags.id')))

class Setting(Base):
    __tablename__='settings'
    id=Column(Integer, primary_key=True)
    music_dir=Column(String)

class Track(Base):
    __tablename__='tracks'
    id=Column(Integer, primary_key=True)
    path=Column(String, unique=True)
    name=Column(String)
    size=Column(Integer)
    waveform=Column(Text)
    tags=relationship('Tag', secondary=track_tag, back_populates='tracks')

class Tag(Base):
    __tablename__='tags'
    id=Column(Integer, primary_key=True)
    name=Column(String, unique=True)
    tracks=relationship('Track', secondary=track_tag, back_populates='tags')

engine=create_engine('sqlite:///music_player.sqlite')
Base.metadata.create_all(engine)
Session=sessionmaker(bind=engine)

# ================= SERVICES =================
class MusicService:
    def __init__(self, s): self.s=s
    def scan(self, folder):
        for f in Path(folder).rglob("*.mp3"):
            if not self.s.query(Track).filter_by(path=str(f)).first():
                self.s.add(Track(path=str(f), name=f.name, size=f.stat().st_size))
        self.s.commit()
        return self.s.query(Track).all()

class WaveThread(QThread):
    done=pyqtSignal(list)
    def __init__(self, path): super().__init__(); self.path=path
    def run(self):
        try:
            audio=AudioSegment.from_file(self.path)
            data=np.array(audio.get_array_of_samples())
            chunk=max(1,len(data)//400)
            wf=[int(np.max(np.abs(data[i:i+chunk]))) for i in range(0,len(data),chunk)]
            self.done.emit(wf[:400])
        except:
            self.done.emit([0]*400)

# ================= UI =================
class Wave(QWidget):
    def __init__(self, seek_cb):
        super().__init__(); self.data=[]; self.p=0; self.seek_cb=seek_cb
    def set(self,d): self.data=d; self.update()
    def prog(self,v): self.p=v; self.update()
    def mousePressEvent(self,e):
        if self.data: self.seek_cb(e.position().x()/self.width())
    def paintEvent(self,e):
        if not self.data: return
        p=QPainter(self); w,h=self.width(),self.height()
        step=w/len(self.data); m=max(self.data) or 1
        for i,v in enumerate(self.data):
            x=i*step; bar=(v/m)*h
            p.setPen(QColor('#00ffaa') if i/len(self.data)<self.p else QColor('#444'))
            p.drawLine(int(x), int(h/2-bar/2), int(x), int(h/2+bar/2))

class TagFilter(QComboBox):
    def __init__(self): super().__init__(); self.setModel(QStandardItemModel())
    def load(self, tags):
        self.clear()
        for t in tags:
            it=QStandardItem(t.name); it.setCheckable(True); it.setData(t.id)
            self.model().appendRow(it)
    def checked(self):
        return [self.model().item(i).data() for i in range(self.model().rowCount()) if self.model().item(i).checkState()==Qt.CheckState.Checked]

# ================= PLAYER =================
class Player(QWidget):
    def __init__(self):
        super().__init__()
        self.s=Session(); self.music=MusicService(self.s)
        self.player=QMediaPlayer(); self.audio=QAudioOutput(); self.player.setAudioOutput(self.audio)

        self.init_ui(); self.load_settings(); self.load_all()

        self.timer=QTimer(); self.timer.timeout.connect(self.update); self.timer.start(200)

    def init_ui(self):
        self.resize(900,700)
        L=QVBoxLayout(self)

        self.title=QLabel("-"); L.addWidget(self.title)
        self.wave=Wave(self.seek); self.wave.setMinimumHeight(120); L.addWidget(self.wave)
        self.time=QLabel(); L.addWidget(self.time)

        c=QHBoxLayout()
        self.prev=QPushButton("<"); self.play=QPushButton("▶"); self.next=QPushButton(">")
        c.addWidget(self.prev); c.addWidget(self.play); c.addWidget(self.next)
        L.addLayout(c)

        self.folder=QPushButton("📁"); L.addWidget(self.folder)

        sf=QHBoxLayout()
        self.search=QLineEdit(); self.search.setPlaceholderText("Search")
        self.filter=TagFilter()
        sf.addWidget(self.search); sf.addWidget(self.filter)
        L.addLayout(sf)

        self.list=QListWidget(); L.addWidget(self.list)

        # TAG UI
        tagL=QVBoxLayout()
        row=QHBoxLayout()
        self.tag_in=QLineEdit(); self.add_tag=QPushButton("+")
        row.addWidget(self.tag_in); row.addWidget(self.add_tag)
        tagL.addLayout(row)

        self.tag_box=QVBoxLayout()
        w=QWidget(); w.setLayout(self.tag_box)
        sc=QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(w)
        tagL.addWidget(sc)

        L.addLayout(tagL)

        # signals
        self.play.clicked.connect(self.toggle)
        self.prev.clicked.connect(self.prev_track)
        self.next.clicked.connect(self.next_track)
        self.folder.clicked.connect(self.select_folder)
        self.list.itemClicked.connect(self.play_track)
        self.search.textChanged.connect(self.apply)
        self.filter.model().itemChanged.connect(self.apply)
        self.add_tag.clicked.connect(self.create_tag)

    # ===== SETTINGS =====
    def load_settings(self):
        s=self.s.query(Setting).first()
        if not s:
            s=Setting(music_dir=str(Path.home()/"Music")); self.s.add(s); self.s.commit()
        self.dir=s.music_dir

    def select_folder(self):
        f=QFileDialog.getExistingDirectory(self)
        if f:
            s=self.s.query(Setting).first(); s.music_dir=f; self.s.commit()
            self.dir=f; self.load_all()

    # ===== LOAD =====
    def load_all(self):
        self.tracks=self.music.scan(self.dir)
        self.load_tags()
        self.apply()

    def load_tags(self):
        tags=self.s.query(Tag).all()
        self.filter.load(tags)

        # checkbox list
        for i in reversed(range(self.tag_box.count())):
            w=self.tag_box.itemAt(i).widget()
            if w: w.deleteLater()

        self.tag_checks={}
        for t in tags:
            cb=QCheckBox(t.name)
            cb.stateChanged.connect(lambda st, tag=t: self.toggle_tag(tag, st))
            self.tag_box.addWidget(cb)
            self.tag_checks[t.id]=cb

    # ===== FILTER =====
    def apply(self):
        txt=self.search.text().lower(); f_ids=self.filter.checked()
        self.list.clear()
        for t in self.tracks:
            if txt and txt not in t.name.lower(): continue
            if f_ids:
                ids=[tg.id for tg in t.tags]
                if not all(i in ids for i in f_ids): continue
            it=QListWidgetItem(t.name); it.setData(Qt.ItemDataRole.UserRole,t.id)
            self.list.addItem(it)

    # ===== PLAY =====
    def play_track(self,item):
        self.cur=self.s.get(Track,item.data(Qt.ItemDataRole.UserRole))
        self.title.setText(self.cur.name)
        self.player.setSource(QUrl.fromLocalFile(self.cur.path))
        self.player.play(); self.play.setText("⏸")

        if self.cur.waveform:
            self.wave.set(json.loads(self.cur.waveform))
        else:
            self.thread=WaveThread(self.cur.path)
            self.thread.done.connect(self.save_wave)
            self.thread.start()

        self.sync_tags()

    def save_wave(self,wf):
        self.wave.set(wf)
        self.cur.waveform=json.dumps(wf)
        self.s.commit()

    def toggle(self):
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause(); self.play.setText("▶")
        else:
            self.player.play(); self.play.setText("⏸")

    def prev_track(self):
        r=self.list.currentRow()
        if r>0: self.list.setCurrentRow(r-1); self.play_track(self.list.currentItem())

    def next_track(self):
        r=self.list.currentRow()
        if r<self.list.count()-1: self.list.setCurrentRow(r+1); self.play_track(self.list.currentItem())

    def seek(self,ratio):
        if self.player.duration(): self.player.setPosition(int(self.player.duration()*ratio))

    def update(self):
        if self.player.duration():
            pos=self.player.position(); dur=self.player.duration()
            self.wave.prog(pos/dur)
            f=lambda ms: f"{(ms//1000)//60}:{(ms//1000)%60:02d}"
            self.time.setText(f"{f(pos)} / {f(dur)}")

    # ===== TAGS =====
    def create_tag(self):
        name=self.tag_in.text().strip()
        if not name: return
        if not self.s.query(Tag).filter_by(name=name).first():
            self.s.add(Tag(name=name)); self.s.commit()
        self.tag_in.clear(); self.load_tags(); self.apply()

    def toggle_tag(self,tag,state):
        if not hasattr(self,'cur'): return
        if state==Qt.CheckState.Checked.value:
            if tag not in self.cur.tags: self.cur.tags.append(tag)
        else:
            if tag in self.cur.tags: self.cur.tags.remove(tag)
        self.s.commit()

    def sync_tags(self):
        for tid,cb in self.tag_checks.items():
            tag=self.s.get(Tag,tid)
            cb.setChecked(tag in self.cur.tags)

# ================= RUN =================
if __name__=='__main__':
    app=QApplication(sys.argv)
    w=Player(); w.show()
    sys.exit(app.exec())