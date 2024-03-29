from typing import List, Any
from Grid import sortKey

from jsonIO import CLS_JsonReader, CLS_JsonSaver
import os

def time2beat(time, offset, bpm):
    return (time - offset) * bpm / 60

class CLS_Note(object):
    def __init__(self, noteinfo: dict, bpm, offset):
        # self.idx = -1
        self.bpm, self.offset = bpm, offset
        if noteinfo is None:
            return
        # self.noteinfo = noteinfo
        # notetest = dict(Type="test", Rail=-2, Length=0.0, StartTime=1.0, DelayTime=2.0)
        self.type = noteinfo["Type"]
        self.rail = noteinfo["Rail"]
        self.timeLengthBeat = time2beat(noteinfo["Length"], self.offset, self.bpm)
        self.spawnBeat = time2beat(noteinfo["StartTime"] - noteinfo["DelayTime"], self.offset, self.bpm)
        self.touchBeat = time2beat(noteinfo["StartTime"], self.offset, self.bpm)

    def beat2time(self, beat):
        return self.offset + (beat - self.offset * self.bpm / 60) / self.bpm * 60

    def revertBeatToTimeInfo(self):
        st = self.beat2time(self.touchBeat) + self.offset
        dt = st - self.beat2time(self.spawnBeat)
        tl = self.beat2time(self.timeLengthBeat)
        return dict(Type=self.type, Rail=self.rail, Length=tl, StartTime=st, DelayTime=dt)

    def get_info(self):
        return [self.type, self.rail, self.spawnBeat, self.touchBeat, self.timeLengthBeat]


class CLS_ChartManager(CLS_JsonSaver):
    noteList: List[CLS_Note]

    def sortKey(note):
        return note.touchBeat

    def __init__(self, path):
        super(CLS_ChartManager, self).__init__(path)
        reader = CLS_JsonReader(path)

        self.chartData = reader.get_content()
        self.chartPath = path
        self.bpm = self.chartData["BPM"] # NOTE: This is a test bpm, bind to tk variable
        self.chartOffset = 0
        self.musicOffset = self.chartData["Offset"]

        self.noteList = []
        self.noteNum = self.chartData["NoteNum"]
        self.chartLength = time2beat(self.chartData["Length"], self.chartOffset, self.bpm)
        self.load_all_notes()

    def save_chart(self):  # NOTE: API function (external use)
        """
        save all current existing note into chart data.
        (Export API)
        """
        self.chartData["NoteNum"] = self.noteNum
        newChartData = [0] * self.noteNum
        for idx in range(self.noteNum):
            newChartData[idx] = self.noteList[idx].revertBeatToTimeInfo()
            newChartData[idx]["StartTime"] += self.chartOffset
        self.chartData["NoteList"] = newChartData
        self.save_content(self.chartData)
        print("successfully saved current noteList")

    def create_note(self, noteinfo=None, Type=None, Rail=None, SpawnBeat=None, TouchBeat=None,
                    TimeLengthBeat=None):  # NOTE: API function (external use)
        """
        construct a new note and add to self.noteList.
        (Export API)

        :param noteinfo: create note with a dict of std noteinfo, if None, need the following 5 variables to construct a new note.
        """
        # create note in either way
        if noteinfo:
            newnote = CLS_Note(noteinfo, self.bpm, self.chartOffset)
        else:
            newnote = CLS_Note(None, self.bpm, self.chartOffset)
            newnote.type, newnote.rail = Type, Rail
            newnote.spawnBeat, newnote.touchBeat, newnote.timeLengthBeat = SpawnBeat, TouchBeat, TimeLengthBeat
        self.add_note(newnote)
        print("successfully add note to noteList,remember to save it to json!")
        return

    def get_id(self, Type, Rail, SpawnBeat, TouchBeat,TimeLengthBeat):
        for i in range(len(self.noteList)):
            if self.noteList[i].type == Type and \
        self.noteList[i].rail == Rail and \
        self.noteList[i].spawnBeat == SpawnBeat and \
        self.noteList[i].touchBeat == TouchBeat and \
        self.noteList[i].timeLengthBeat == TimeLengthBeat:
                return i + 1

    def add_note(self, note: CLS_Note):
        # note.idx = self.noteNum
        self.noteNum += 1
        self.noteList.append(note)
        self.noteList.sort(key = sortKey)

    def load_all_notes(self):
        idx = 0
        self.noteList = [0] * self.chartData["NoteNum"]
        for noteInfo in self.chartData["NoteList"]:
            self.noteList[idx] = CLS_Note(noteInfo, self.bpm, self.chartOffset)
            # self.noteList[idx].idx = idx
            idx += 1
        return

    def delete_note(self, id):
        self.noteNum -= 1
        del self.noteList[id - 1]

    def modify_note(self, id, noteinfo, Type, Rail, SpawnBeat, TouchBeat,
                    TimeLengthBeat):
        self.noteList[id - 1].type = Type
        self.noteList[id - 1].rail = Rail
        self.noteList[id - 1].spawnBeat = SpawnBeat
        self.noteList[id - 1].touchBeat =TouchBeat
        self.noteList[id - 1].timeLengthBeat = TimeLengthBeat
        self.noteList.sort(key = sortKey)

    def copy_note(self, cStartBeat, cEndBeat, pStartBeat, flip):
        for note in self.noteList:
            if cStartBeat <= note.touchBeat <= cEndBeat:
                adj = pStartBeat - cStartBeat
                rail = note.rail
                if flip == 'flip':
                    rail = - rail
                self.create_note(None, note.type, rail, note.spawnBeat + adj
                                    , note.touchBeat + adj, note.timeLengthBeat)

class CLS_DataManager(object):
    def __init__(self):
        pass

    def load(self, rootpath):
        """
        Manage all json data of a song.
        :param rootpath: the root directory path, should be ./Charts/SongName
        """
        self.rootpath = rootpath
        reader = CLS_JsonReader()
        # get metadata
        self.metapath = os.path.join(rootpath, "meta.json")
        reader.reread(self.metapath)
        self.metadata = reader.get_content()
        
        
        self.musicpath = os.path.join(rootpath, self.metadata["MusicFile"])
        
        # get charts
        self.chartManagers = {}  # difficulty name to CLS_ChartManager instance
        for difficulty in self.metadata["Difficulties"]:
            dname = difficulty["DifficultyName"]
            chart_identifier = "chart" + str(difficulty["Difficulty"]) + ".json"
            chartpath = os.path.join(rootpath, chart_identifier)

            self.chartManagers[dname] = CLS_ChartManager(chartpath)
            self.chartpath = os.path.join(rootpath, chartpath)
            self.meta_saver = CLS_JsonSaver(self.chartpath)
        reader.close()

    def save_all_data(self):
        '''
        should not be used when lock feature is used.
        :return:
        '''
        self.save_meta()
        for CM in self.chartManagers:
            CM.save_chart()
        print(f"Saving complete.Saved meta and {len(self.chartManagers)} charts")
        return

    def save_meta(self):
        self.meta_saver.save_content(self.metadata)

    def save_chart_by_difficulty(self, difficulty):
        self.chartManagers[difficulty].save_chart()


if __name__ == "__main__":
    DM = CLS_DataManager("./Charts/StillAlive")
    CM = DM.chartManagers["Easy"]

    # change note
    print(CM.noteList[0].get_info())
    CM.noteList[0].spawnBeat -= 1
    print(CM.noteList[0].get_info())

    # add note
    # notetest = dict(Type="test", Rail=-2, Length=0.0, StartTime=1.0, DelayTime=2.0)
    # CM.add_note(notetest)

    # save all
    CM.save_chart()

# TODO:
#  need to rearrange json by ascending StartTime.
#  delete node option
#  can add difficulty and corresponding chart file
