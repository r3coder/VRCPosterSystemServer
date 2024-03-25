# Discord bot to handle user poster requests
# Uses interactions.py

import os
import sys
import time
import json
import random

import interactions
from interactions.ext.tasks import IntervalTrigger, create_task

import urllib.request

opener=urllib.request.build_opener()
opener.addheaders=[('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'), ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'), ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'), ('Connection', 'keep-alive')]
urllib.request.install_opener(opener)

import asyncio
from datetime import datetime, timedelta

# convert %Y/%m/%d %H:%M:%S to "%m월 %d일 %H시" input is string
def HumanTime(t):
    return datetime.strptime(t, "%Y/%m/%d %H:%M:%S").strftime("%m월 %d일 %H시")

def Now(gmt=9):
    return datetime.now() + timedelta(hours=gmt)

def ParseTimeInput(s):
    try:
        # format: YYYY/MM/DD HH:MM:SS
        v = datetime.strptime(s, "%Y/%m/%d %H:%M:%S")
        return v.strftime("%Y/%m/%d %H:%M:%S")
    except:
        try:
            # format: YYYY/MM/DD HH:MM
            v = datetime.strptime(s, "%Y년 %m월 %d일 %H시")
            return v.strftime("%Y/%m/%d %H:%M:%S")
        except:
            try:
                # format: YYYYMMDDHH
                v = datetime.strptime(s, "%Y%m%d%H")
                return v.strftime("%Y/%m/%d %H:%M:%S")
            except:
                try:
                    # format : YYYYMMDD
                    v = datetime.strptime(s, "%Y%m%d")
                    return v.strftime("%Y/%m/%d %H:%M:%S")
                except:
                    printl(f'(ParseTime) Time {s} is not valid.')
                    return None

def DumbParserTime(s):
    s = s.replace(" ","").replace("년","/").replace("월","/").replace("일"," ").replace("시","").replace("분","").replace("초","")
    return datetime.strptime(s, "%Y/%m/%d %H")

def AddPosterEmbed(embed, poster, brief = True):
    pos = poster["postPosition"]
    pid = poster["formId"]
    desc = poster["description"]
    posterURL = poster["posterURL"]
    pt = poster["posttime"]
    et = poster["endtime"]
    if brief:
        embed.add_field(
            name=f"`#{pid}` - <#{pid}> - {pos}",
            value=f"{pt} ~ {et}\n{posterURL}",
            inline=False
        )
    else:
        embed.add_field(
            name=f"`#{pid}` - <#{pid}> - {pos}",
            value=f"게시 시작시간 : {pt}\n게시 종료시간 : {et}\n이미지 : {posterURL}\n설명 : {desc}",
            inline=False
        )

POSTER_STATE_KR = {
    "waiting_agreement": "입력중_동의",
    "waiting_poster_image": "입력중_포스터이미지",
    "waiting_description": "입력중_설명",
    "waiting_posttime": "입력중_시작시간",
    "waiting_endtime": "입력중_종료시간",
    "pending": "대기중",
    "approved": "승인됨",
    "declined": "거절됨",
    "posted" : "게시됨",
    "canceled" : "취소됨",
    "finished": "게시 종료됨"
}

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

class DBManager():
    def __init__(self, path = "./db"):
        self.path = path
        self.posterForms = dict()

        # Log file
        if not os.path.exists('logs'):
            os.makedirs('logs')
        # current time as current timezone
        self.log_file_path = os.path.join('logs', f'{Now().strftime("%Y%m%d_%H%M%S")}.log')
        print(f'(DBManager) Log file path: {self.log_file_path}')

    def AddPosterForm(self, posterId, authorid):
        p = PosterForm(posterId, authorid)
        self.posterForms[posterId] = p
    
    def UpdatePostedPoster(self, postPosition, time):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):                
                with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                    d = json.load(f)
                    if d["state"] == "posted" and d["postPosition"] == postPosition:
                        posterId = d["formId"]
                        d["endtime"] = time
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                        printl(f'(UpdatePostedPoster) Poster {posterId} endtime is updated to {Now().strftime("%Y/%m/%d %H:%M:%S")}.')
                        return True
        return False
    
    def ApprovePoster(self, posterId, postPosition, force):
        # Search every posterid in archive, with approved and posted state
        posters = []
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == posterId:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        if d["postPosition"] == postPosition and d["state"] == "approved" or d["state"] == "posted":
                            posters.append(d)
        
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == posterId:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        if d["state"] != "pending":
                            return False
                        # Check if any time domain is overlapped
                        overlap = False
                        cpt = datetime.strptime(d["posttime"], "%Y/%m/%d %H:%M:%S")
                        cet = datetime.strptime(d["endtime"], "%Y/%m/%d %H:%M:%S")
                        for p in posters:
                            if p["postPosition"] == postPosition:
                                pt = datetime.strptime(p["posttime"], "%Y/%m/%d %H:%M:%S")
                                et = datetime.strptime(p["endtime"], "%Y/%m/%d %H:%M:%S")
                                if (pt < cpt and cpt < et) or (pt < cet and cet < et) or (cpt < pt and cet > et):
                                    overlap = True
                                    break
                        if force:
                            overlap = False
                        if overlap:
                            printl(f'(ApprovePoster) Poster {posterId} has been not approved sice time overlap. Enable force to approve.')
                            return False, None, None
                        d["state"] = "approved"
                        d["postPosition"] = postPosition
                        # If posttime is before now, set posttime to next hour 0:00
                        if datetime.strptime(d["posttime"], "%Y/%m/%d %H:%M:%S") < Now():
                            d["posttime"] = (Now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).strftime("%Y/%m/%d %H:%M:%S")
                            printl(f'(ApprovePoster) Poster {posterId} time has been changed to {d["posttime"]}.')
                        d["timestamp"]["approved"] = Now().strftime("%Y/%m/%d %H:%M:%S")
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                        printl(f'(ApprovePoster) Poster {posterId} has been approved.')
                        if force:
                            self.UpdatePostedPoster(postPosition, d["posttime"])
                        return True, d["posttime"], d["endtime"]
        return False, None, None
    
    def DeclinePoster(self, posterId, reason):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == posterId:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        if d["state"] != "pending":
                            return False
                        d["state"] = "declined"
                        d["declineReason"] = reason
                        d["timestamp"]["declined"] = Now().strftime("%Y/%m/%d %H:%M:%S")
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                        printl(f'(DeclinePoster) Poster {posterId} has been declined.')
                        return True
        return False

    def CancelPoster(self, posterId):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == posterId:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        d["state"] = "canceled"
                        d["timestamp"]["canceled"] = Now().strftime("%Y/%m/%d %H:%M:%S")
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                        printl(f'(CancelPoster) Poster {posterId} has been canceled.')
                        return True


    def GetPostersInfo(self, state):
        res = []
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                    d = json.load(f)
                    if d["state"] == state:
                        res.append(d)
        return res

    def GetPostersPosition(self, pos):
        res = []
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                    d = json.load(f)
                    if d["postPosition"] == pos and d["state"] in ["approved", "posted"]:
                        res.append(d)
        return res

    def PostPoster(self):
        sta, end = {}, {}
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                    d = json.load(f)
                    # if current time is between posttime and endtime
                    pt = datetime.strptime(d["posttime"], "%Y/%m/%d %H:%M:%S")
                    et = datetime.strptime(d["endtime"], "%Y/%m/%d %H:%M:%S")
                    if d["state"] == "approved" and pt <= Now():
                        # if state is pending, change state to posted
                        d["state"] = "posted"
                        d["timestamp"]["posted"] = Now().strftime("%Y/%m/%d %H:%M:%S")
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                        postTarget = d["postPosition"]
                        os.system(f'cp {os.path.join(self.path, "archive", year, folder, "poster.png")} {os.path.join(self.path, "online", f"{postTarget}.png")}')
                        printl(f'(PostPoster) Poster {folder} has been posted to {postTarget}.')
                        sta[folder] = d["postPosition"]
                    if d["state"] == "posted" and et <= Now():
                        # if state is posted, change state to finished
                        d["state"] = "finished"
                        d["timestamp"]["finished"] = Now().strftime("%Y/%m/%d %H:%M:%S")
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                        printl(f'(PostPoster) Poster {folder} has been finished.')
                        end[folder] = d["postPosition"]
        return sta, end
                    

    def SavePosterDB(self):
        # create folder by year
        year = datetime.fromtimestamp(time.time()).strftime("%Y%m")
        if not os.path.exists(os.path.join(self.path, "archive", year)):
            os.makedirs(os.path.join(self.path, "archive", year))

        if len(self.posterForms) == 0:
            return
        # check every poster forms and check if it is time to post
        rml = []
        for posterId in self.posterForms:
            pf = self.posterForms[posterId]
            # Save poster year by "posttime"
            ymd = datetime.fromtimestamp(pf.posttime).strftime("%Y%m%d")
            folderpath = f'{pf.formId}'

            if os.path.exists(os.path.join(self.path, "archive", year, folderpath)):
                # remane folder, add "_old" + random number
                os.rename(os.path.join(self.path, "archive", year, folderpath), os.path.join(self.path, "archive", year, folderpath + "_old" + str(random.randint(0, 10000))))
                printl(f'(SavePosterDB) Old poster has been replaced.')

            os.makedirs(os.path.join(self.path, "archive", year, folderpath))
            try:
                urllib.request.urlretrieve(pf.posterURL, os.path.join(self.path, "archive", year, folderpath, "poster.png"))
                printl(f'(SavePosterDB) Poster image been downloaded from {pf.posterURL} to {os.path.join(self.path, year, folderpath, "poster.png")}')
            except:
                printl(f'(SavePosterDB) Poster image download failed.')

            with open(os.path.join(self.path, "archive", year, folderpath, "info.json"), 'w') as f:
                json.dump(pf.GetDict(), f)
                printl(f'(SavePosterDB) PosterForm has been saved to {os.path.join(self.path, "archive", year, folderpath, "info.json")}')
            rml.append(posterId)
        for posterId in rml:
            self.posterForms.pop(posterId)
    
    def GetPosterEmbed(self, pid):
        posterDict = self.GetPosterInfo(pid)
        if posterDict != None:
            userid = posterDict["userid"]
            embed = interactions.Embed(title=f"포스터 {pid} 정보", description="", color=0x00ff00)
            embed.add_field(name="포스터 이미지", value=posterDict["posterURL"], inline=False)
            embed.add_field(name="포스터 설명", value=posterDict["description"], inline=False)
            embed.add_field(name="게시 시작 시각", value=posterDict["posttime"], inline=False)
            embed.add_field(name="게시 종료 예정 시각", value=posterDict["endtime"], inline=False)
            embed.add_field(name="포스터 상태", value=POSTER_STATE_KR[posterDict["state"]], inline=False)
            embed.add_field(name="포스터 신청자", value=f"<@{userid}>", inline=False)
            if posterDict["state"] == "declined":
                embed.add_field(name="거절 사유", value=posterDict["declineReason"], inline=False)
            if posterDict["state"] in ["approved", "posted", "finished"]:
                embed.add_field(name="게시 위치", value=posterDict["postPosition"], inline=False)
        else:
            embed = interactions.Embed(title=f"포스터 {pid} 정보", description="", color=0xff0000)
            embed.add_field(name="포스터 정보", value="포스터 정보를 찾을 수 없습니다.", inline=False)
        return embed

    def GetPosterInfo(self, pid):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == pid:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        try:
                            printl(f'(GetPosterInfo) PosterForm {pid} found.')
                            d = json.load(f)
                            return d
                        except:
                            pass
        printl(f'(GetPosterInfo) PosterForm {pid} not found.')
        return None

    def ChangePosterPostTime(self, pid, posttime):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == pid:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        try:
                            v = datetime.strptime(posttime, "%Y/%m/%d %H:%M:%S")
                        except:
                            printl(f'(ChangePosterPostTime) PosterForm {pid} posttime is not valid.')
                            return False
                        d["posttime"] = posttime
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                            printl(f'(ChangePosterPostTime) PosterForm {pid} posttime changed to {posttime}.')
                            return True
        printl(f'(ChangePosterPostTime) PosterForm {pid} not found.')
        return False

    def ChangePosterEndTime(self, pid, endtime):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == pid:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        try:
                            v = datetime.strptime(endtime, "%Y/%m/%d %H:%M:%S")
                        except:
                            printl(f'(ChangePosterEndTime) PosterForm {pid} posttime is not valid.')
                            return False
                        # write endtime as string YYYY/MM/DD HH:MM:SS
                        d["endtime"] = endtime
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                            printl(f'(ChangePosterEndTime) PosterForm {pid} posttime changed to {endtime}.')
                            return True
        printl(f'(ChangePosterEndTime) PosterForm {pid} not found.')
        return False
    
    def ChangePosterImage(self, pid, url):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == pid:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        try:
                            urllib.request.urlretrieve(url, os.path.join(self.path, "archive", year, folder, "poster.png"))
                            printl(f'(ChangePosterImage) Poster image been downloaded from {url} to {os.path.join(self.path, year, folder, "poster.png")}')
                        except:
                            printl(f'(ChangePosterImage) Poster image download failed.')
                        d["posterURL"] = url
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                            printl(f'(ChangePosterImage) PosterForm {pid} image changed to {url}.')
                            return True
    
    def ChangePosterPosition(self, pid, pos):
        for year in os.listdir(os.path.join(self.path, "archive")):
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                if folder == pid:
                    with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                        d = json.load(f)
                        d["postPosition"] = pos
                        with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'w') as f:
                            json.dump(d, f)
                            printl(f'(ChangePosterPosition) PosterForm {pid} position changed to {pos}.')
                            return True
        printl(f'(ChangePosterPosition) PosterForm {pid} not found.')
        return False

    def LoadPosterStatus(self):
        # get all folders in ./archive
        for year in os.listdir(os.path.join(self.path, "archive")):
            # Later, add code to disable checking really old posters
            for folder in os.listdir(os.path.join(self.path, "archive", year)):
                with open(os.path.join(self.path, "archive", year, folder, "info.json"), 'r') as f:
                    d = json.load(f)


class PosterForm():
    def __init__(self, formId, authorid):
        self.timestamp = dict()
        self.timestamp["created"] = Now().strftime("%Y/%m/%d %H:%M:%S")
        self.state = "waiting_agreement"
        self.formId = str(formId)

        self.posterURL = ""
        self.description = ""
        self.posttime = 0
        self.endtime = 0
        self.postPosition = 0
        self.declineReason = ""
        self.userid = str(authorid)

        printl(f'(PosterForm) PosterForm has been created. {self.timestamp["created"]}, {self.formId}')

    def ChangeState(self, state, ext=None):
        self.state = state
        if state == "approved":
            self.postPosition = ext
        if state == "declined":
            self.declineReason = ext
        self.timestamp[state] = Now().strftime("%Y/%m/%d %H:%M:%S")

    def GetDict(self):
        d = {
            "timestamp": self.timestamp,
            "state": self.state,
            "formId": self.formId,
            "posterURL": self.posterURL,
            "description": self.description,
            "posttime": datetime.fromtimestamp(self.posttime).strftime("%Y/%m/%d %H:%M:%S"),
            "endtime": datetime.fromtimestamp(self.endtime).strftime("%Y/%m/%d %H:%M:%S"),
            "postPosition": self.postPosition,
            "declineReason": self.declineReason,
            "userid": self.userid
        }
        return d

Manager = DBManager()

def printl(msg, *args, **kwargs):
    v = Now().isoformat(sep=' ', timespec="milliseconds")
    print(f'{v} [INFO] {msg}', *args, **kwargs)
    with open(Manager.log_file_path, 'a') as f:
        f.write(f'{v} [INFO] {msg}\n')

bot = interactions.Client(TOKEN, intents=interactions.Intents.DEFAULT | interactions.Intents.GUILD_MESSAGE_CONTENT)

CHANNEL_ID = 1090617603061465158


@create_task(IntervalTrigger(60))
async def IntervalTask():
    # Get channel by name
    channel = await interactions.get(bot, interactions.Channel, object_id=CHANNEL_ID)
    # await channel.send(":)")
    # current time using time
    now = datetime.now() + timedelta(hours=9)

    if Now().minute == 0:
        printl(f'(IntervalTask) Updating poster')
        sta, end = Manager.PostPoster()
        for key in sta:
            printl(f'(IntervalTask) Poster {key} has been posted.')
            v = sta[key]
            embed = interactions.Embed(title=f"아래 포스터가 자리 {v}에 게시되었습니다.", description="", color=0x00ff00)
            await channel.send("", embeds=embed)
            embed = Manager.GetPosterEmbed(key)
            await channel.send("", embeds=embed)
            chan = await interactions.get(bot, interactions.Channel, object_id=key)
            embed = interactions.Embed(title="포스터가 게시되었습니다.", description="게임 내 게시 여부를 확인해 주세요. 만일 게시가 되지 않았을 경우에는 메세지를 남겨주세요.", color=0x00ff00)
            await chan.send(embeds=embed)
        for key in end:
            printl(f'(IntervalTask) Poster {key} has been finished.')
            v = end[key]
            embed = interactions.Embed(title=f"아래 포스터가 자리 {v}에서 게시 종료되었습니다.", description="다른 포스터 게시까지는 그 자리에 계속 게시됩니다. 티켓을 꼭 닫아주세요.", color=0xff0000)
            await channel.send("", embeds=embed)
            embed = Manager.GetPosterEmbed(key)
            await channel.send("", embeds=embed)
            chan = await interactions.get(bot, interactions.Channel, object_id=key)
            embed = interactions.Embed(title="포스터 게시가 종료되었습니다.", description="티켓을 삭제해도 무방합니다.", color=0x00ff00)
            await chan.send(embeds=embed)
        
    
    lls = []
    for key in Manager.posterForms:
        if "waiting" in Manager.posterForms[key].state:
            # Time string to datetime
            createdTime = datetime.strptime(Manager.posterForms[key].timestamp["created"], "%Y/%m/%d %H:%M:%S")
            # check if 1 minute passed from createdTime
            if createdTime > now + timedelta(minutes=60):
                printl(f'(IntervalTask) Ticket {key} is deleted. (timeout)')
                lls.append(key)
                channel = await interactions.get(bot, interactions.Channel, object_id=key)
                embed = interactions.Embed(title="포스터 신청이 취소되었습니다.", description="포스터 신청이 1시간 이상 진행되지 않아 취소되었습니다. `/포스터신청` 명령어를 이용해 다시 신청해 주세요.", color=0xff0000)
                await channel.send(embeds=embed)
    for key in lls:
        del Manager.posterForms[key]
                

task_started = False
@bot.event
async def on_ready():
    printl(f'(on_ready) Bot is prepared.')
    # Manager.LoadPosterStatus()
    global task_started
    if task_started == False:
        print(f'Interval Task has been initialized.')
        IntervalTask.start()
        task_started = True


@bot.event
async def on_message_create(ctx: interactions.CommandContext):
    if ctx.author.bot:
        return

    if ctx.channel_id in Manager.posterForms:
        embed = None
        pf = Manager.posterForms[ctx.channel_id]
        if pf.state == "waiting_agreement":
            if ctx.content in ["동의합니다", "동의합니다.", "동의합니다!", "동의합니다!", "위 내용에 동의합니다", "위 내용에 동의합니다.", "위 내용에 동의합니다!"]:
                embed = interactions.Embed(
                    title="포스터 신청 단계 (2/5)",
                    description="포스터 신청 유의사항에 동의하셨습니다.\n\n2. 포스터 이미지를 올려주세요.\n - 하나의 png 파일만 올려주세요.\n - 최대 용량은 5MB 입니다.\n - 포스터의 비율이 A4 세로가 아닐 시, 자동으로 리사이징됩니다.\n - 가로 혹은 세로 크기가 2000 픽셀보다 큰 이미지는 등록할 수 없습니다.\n - 1시간 이내에 등록을 완료해 주세요.",
                    color=0x00ff00
                )
                pf.ChangeState("waiting_poster_image")
                printl(f'(PosterEnroll) Form {ctx.channel_id} Accepted, state:{pf.state}')
            else:
                embed = interactions.Embed(title=":x: 동의하지 않으셨습니다. 신청이 취소됩니다. 다시 신청해주세요.",color=0xff0000)
                printl(f'(PosterEnroll) Form {ctx.channel_id} declined, deleting form')
                del Manager.posterForms[ctx.channel_id]
        elif pf.state == "waiting_poster_image":
            if ctx.attachments:
                for attachment in ctx.attachments:
                    if not attachment.filename.endswith(".png"):
                        embed = interactions.Embed(title=":x: 포스터의 이미지가 png 포맷이 아닙니다. 다시 올려주세요.", color=0xff0000)
                        printl(f'(PosterEnroll) Form {ctx.channel_id} attachment is not png')
                    # attachment width, height
                    elif attachment.width  > 2000 or attachment.height > 2000:
                        embed = interactions.Embed(title=":x: 포스터의 해상도가 너무 높습니다. 포스터의 큰 변이 2000px가 넘지 않도록 포스터 크기를 조정해서 다시 올려주세요.", color=0xff0000)
                        printl(f'(PosterEnroll) Form {ctx.channel_id} attachment resolution is too high')
                    elif attachment.size > 5 * 1024 * 1024:
                        embed = interactions.Embed(title=":x: 포스터의 용량이 5MB를 초과합니다. 다시 올려주세요.", color=0xff0000)
                        printl(f'(PosterEnroll) Form {ctx.channel_id} attachment size exceeded 10MB')
                    else:
                        desc = ":white_check_mark: 포스터 이미지가 인식 되었습니다.\n"
                        if abs(attachment.width / attachment.height - 210 / 297) > 0.05:
                            desc = ":warning: 포스터의 비율이 A4 세로가 아닙니다.(이미지가 왜곡될 가능성이 있습니다.)\n"
                            printl(f'(PosterEnroll) Form {ctx.channel_id} attachment ratio is not A4')
                        desc = desc + "포스터 이미지가 등록되었습니다.\n\n3. 포스터 / 해당 이벤트에 대한 설명을 간단히 적어주세요 (200자 이내)."
                        embed = interactions.Embed(title="포스터 신청 단계 (3/5)", description=desc, color=0x00ff00)
                        pf.posterURL = attachment.url
                        pf.ChangeState("waiting_description")
                        printl(f'(PosterEnroll) Form {ctx.channel_id} image accepted, state:{pf.state}')
            else:
                embed = interactions.Embed(title="포스터 이미지를 올려주세요.",color=0xff0000)
                printl(f'(PosterEnroll) Form {ctx.channel_id} attachment not found')
        elif pf.state == "waiting_description":
            if len(ctx.content) > 200:
                embed = interactions.Embed(title=":x: 설명이 너무 깁니다. 200자 이내로 다시 적어주세요.",color=0xff0000)
                printl(f'(PosterEnroll) Form {ctx.channel_id} description too long')
            else:
                cy, cm, cd, ch = Now().year, Now().month, Now().day, Now().hour
                embed = interactions.Embed(
                    title="포스터 신청 단계 (4/5)",
                    description=f"포스터 설명이 등록되었습니다.\n\n4. 포스터의 희망 게시 시작 날짜와 시간을 `{cy}년 {cm}월 {cd}일 {ch}시` 양식에 맞춰 적어주세요.\n - 12시 기준이 아닌 24시 기준으로 적어주세요.\n - 24시는 0시로 입력해 주세요. \n - 현재 시간보다 과거의 시간을 입력할 수는 없습니다.",
                    color=0x00ff00
                )
                pf.description = ctx.content
                pf.ChangeState("waiting_posttime")
                printl(f'(PosterEnroll) Form {ctx.channel_id} description accepted, state:{pf.state}')
        elif pf.state == "waiting_posttime":
            # If message doesn't start with number, pass
            if not ctx.content[0].isdigit():
                pass
            flag = False
            try:
                # parse yyyy/mm/dd HH:MM to datetime
                pf.posttime = DumbParserTime(ctx.content).timestamp()
                flag = True
            except ValueError:
                embed = interactions.Embed(title=":x: 날짜 형식이 잘못되었습니다. 다시 적어주세요.",color=0xff0000)
                printl(f'(PosterEnroll) Form {ctx.channel_id} posttime format error')
            
            if flag:
                if pf.posttime < time.time():
                    embed = interactions.Embed(title=":x: 신청 시간이 과거입니다. 다시 적어주세요.",color=0xff0000)
                    printl(f'(PosterEnroll) Form {ctx.channel_id} posttime is in the past')
                else:
                    cy, cm, cd, ch = Now().year, Now().month, Now().day, Now().hour
                    embed = interactions.Embed(
                        title="포스터 신청 단계 (5/5)",
                        description=f"포스터 희망 게시 시작 일시가 입력되었습니다.\n\n5. 포스터의 희망 게시 종료 시각을 `{cy}년 {cm}월 {cd}일 {ch}시` 양식에 맞춰 적어주세요.\n - 12시 기준이 아닌 24시 기준으로 적어주세요.\n - 24시는 0시로 입력해 주세요. \n - 현재 시간보다 과거의 시간을 입력할 수는 없습니다.\n - 신청 시각보다 14일 이후의 시간은 입력할 수 없습니다.",
                        color=0x00ff00
                    )
                    pf.ChangeState("waiting_endtime")
                    printl(f'(PosterEnroll) Form {ctx.channel_id} posttime accepted, state:{pf.state}')
        elif pf.state == "waiting_endtime":
            flag = False
            try:
                pf.endtime = DumbParserTime(ctx.content).timestamp()
                flag = True
            except ValueError:
                embed = interactions.Embed(title=":x: 날짜 형식이 잘못되었습니다. 다시 적어주세요.",color=0xff0000)
                printl(f'(PosterEnroll) Form {ctx.channel_id} endtime format error')
            
            if flag:
                if pf.endtime < time.time():
                    embed = interactions.Embed(title=":x: 신청 시간이 과거입니다. 다시 적어주세요.",color=0xff0000)
                    printl(f'(PosterEnroll) Form {ctx.channel_id} endtime is in the past')
                elif pf.endtime < pf.posttime:
                    embed = interactions.Embed(title=":x: 게시 종료 시간이 게시 시작 시간보다 빠릅니다. 다시 적어주세요.",color=0xff0000)
                    printl(f'(PosterEnroll) Form {ctx.channel_id} endtime is before posttime')
                # Check 14 days
                elif pf.endtime - pf.posttime > timedelta(days=14).total_seconds():
                    embed = interactions.Embed(title=":x: 게시 기간이 14일을 초과합니다. 다시 적어주세요.",color=0xff0000)
                    printl(f'(PosterEnroll) Form {ctx.channel_id} endtime - posttime is over 14 days')
                else:
                    pf.ChangeState("pending")
                    Manager.SavePosterDB()
                    embed = interactions.Embed(
                        title="포스터 신청이 완료되었습니다.",
                        description="신청이 완료되었습니다. 신청 내용은 아래와 같습니다. 관리자의 승인을 기다려 주세요.",
                        color=0x00ff00
                    )
                    await ctx.reply("", embeds=embed)
                    embed = Manager.GetPosterEmbed(str(ctx.channel_id))
        if embed:
            await ctx.reply("", embeds=embed)

@bot.command(
    name="poster_enroll",
    name_localizations={"ko": "포스터신청"},
    description="포스터를 신청합니다.",
    scope=GUILD,
    options = []
)
async def PosterEnroll(ctx: interactions.CommandContext):
    printl(f'(PosterEnroll) Ticket Id: {ctx.channel.id}')
    if ctx.channel.id not in Manager.posterForms:
        Manager.AddPosterForm(ctx.channel.id, ctx.author.id)
        embed = interactions.Embed(
            title="포스터 신청 단계 (1/5)",
            description="1. 포스터 신청과 관련한 동의 확인 여부입니다. 아래 내용 확인 후, `동의합니다` 라고 정확히 적어주세요.",
            color=0x00ff00
        )
        embed.add_field(
            name="본 포스터 시스템에 대해",
            value="본 포스터 시스템은 한국어권 VRchat 내 여러 이벤트 홍보 및 커뮤니티 활성화를 위해 무상으로 제공되는 서비스입니다. 현재 VRChat 한국어 튜토리얼 월드, 화본역에 포스터 에셋이 게시되어 있습니다."
        )
        embed.add_field(
            name="포스터 신청 주의사항",
            value= " - 한 사람당 한 번에 하나의 포스터만 신청 가능합니다.\n" + 
            " - VRChat 이용약관을 침해할 소지가 있어 보인다면 신청이 거절됩니다.\n" + 
            " - 미풍양속을 해치거나 기타 사회통념에 반하는 내용이 있을 경우 신청이 거절됩니다.\n" + 
            " - 게시판 관리자가 게시가 부적절하다고 판단했을 경우에 거절됩니다.\n"
        )
        await ctx.send("", embeds=embed)
    else:
        embed = interactions.Embed(
            title=":x: 이미 포스터 신청이 진행중입니다.",
            description="이미 포스터 신청이 진행중입니다. 신청이 완료되기 전까지는 다시 신청할 수 없습니다.",
            color=0xff0000
        )
        await ctx.send("", embeds=embed)


@bot.command(
    name="poster_approve",
    name_localizations={"ko": "승인"},
    description="포스터를 승인합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="pos",
            name_localizations={"ko": "위치"},
            description="포스터를 게시할 위치를 지정합니다.",
            type=interactions.OptionType.INTEGER,
            required=True
        ),
        interactions.Option(
            name="force",
            name_localizations={"ko": "강제"},
            description="강제로 승인합니다.",
            type=interactions.OptionType.BOOLEAN
        )
    ]
)
async def PosterAgree(ctx: interactions.CommandContext, pos: int, force: bool = False):
    printl(f'(PosterAgree) Ticket Id: {ctx.channel.id}')
    res, tm, te = Manager.ApprovePoster(str(ctx.channel_id), pos, force)
    if res:
        desc = f"포스터는 {tm} 부터 위치 {pos}에 {te}까지 게시 예정입니다. 게시 종료는 예정보다 빨라질 수 있습니다."
        if force:
            desc += " (이전 시간대를 강제로 조정하고 승인처리 되었습니다.)"
        embed = interactions.Embed(title="포스터 신청이 승인되었습니다.", description=desc, color=0x00ff00)
    else:
        embed = interactions.Embed(title="포스터 승인에 실패했습니다.", description=f"관리자가 처리 예정입니다.", color=0xff0000)
    await ctx.send("", embeds=embed)
    


@bot.command(
    name="poster_decline",
    name_localizations={"ko": "거절"},
    description="포스터를 거절합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="reason",
            description="거절 사유",
            type=interactions.OptionType.STRING,
            required=True
        ),
        interactions.Option(
            name="posterid",
            description="포스터 ID",
            type=interactions.OptionType.STRING
        )
    ]
)
async def PosterDecline(ctx: interactions.CommandContext, reason: str, posterid: str = None):
    if posterid is None:
        posterid = str(ctx.channel_id)
    printl(f'(PosterDecline) reason: {reason}, posterid: {posterid}')
    res = Manager.DeclinePoster(str(ctx.channel_id), reason)
    if res:
        embed = interactions.Embed(title="포스터 신청이 거절되었습니다.", description=f"사유:{reason}", color=0xff0000)
    else:
        embed = interactions.Embed(title=":x: 포스터 ID가 존재하지 않습니다.", description="", color=0xff0000)
    await ctx.send("", embeds=embed)
    

@bot.command(
    name="poster_cancel",
    name_localizations={"ko": "취소"},
    description="포스터를 취소합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="posterid",
            description="포스터 ID",
            type=interactions.OptionType.STRING
        )

    ]
)
async def PosterCancel(ctx: interactions.CommandContext, posterid: str = None):
    if posterid is None:
        posterid = str(ctx.channel_id)
    printl(f'(PosterCancel) posterid: {posterid}')
    res = Manager.CancelPoster(posterid)
    if res:
        embed = interactions.Embed(title="포스터 신청이 취소되었습니다.", description=f"", color=0xff0000)
    else:
        embed = interactions.Embed(title=":x: 포스터 ID가 존재하지 않습니다.", description="", color=0xff0000)
    await ctx.send("", embeds=embed)
    


@bot.command(
    name="information",
    name_localizations={"ko": "정보"},
    description="정보를 조회합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="posterid",
            description="포스터 정보를 조회할 ID입니다.",
            type=interactions.OptionType.STRING
        )
    ]
)
async def PosterInformation(ctx: interactions.CommandContext, posterid: str = None):
    if posterid is None:
        posterid = str(ctx.channel_id)
    printl(f'(PosterInfo) Ticket Id: {posterid}')
    embed = Manager.GetPosterEmbed(posterid)
    await ctx.send("", embeds=embed)


@bot.command(
    name="list",
    name_localizations={"ko": "목록"},
    description="특정 상태의 포스터를 조회합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="state",
            description="포스터 상태를 의미합니다. [posted, pending, approved, declined]",
            type=interactions.OptionType.STRING
        ),
        interactions.Option(
            name="brief",
            description="간략하게 표시합니다.",
            type=interactions.OptionType.BOOLEAN
        )
    ]
)
async def PosterList(ctx: interactions.CommandContext, state: str = "pending", brief: bool = True):
    printl(f'(PosterList) Called with state: {state}')
    if state in POSTER_STATE_KR:
        ss = POSTER_STATE_KR[state]
        embed = interactions.Embed(
            title=f"상태가 '{ss}'인 포스터 목록",
            description="포스터 목록입니다.",
            color=0x00ff00
        )
        pp = Manager.GetPostersInfo(state)
        pp.sort(key=lambda x: x["postPosition"])
        
        if len(pp) == 0:
            embed.add_field(
                name="포스터가 없습니다.",
                value=":drooling_face:",
            )
        else:
            for p in pp:
                AddPosterEmbed(embed, p, brief)
        await ctx.send("", embeds=embed)


@bot.command(
    name="at",
    name_localizations={"ko": "위치"},
    description="특정 위치에 게시된 포스터의 [posted, approved] 정보를 불러옵니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="pos",
            description="게시할 포스터 상태를 의미합니다.",
            type=interactions.OptionType.INTEGER
        ),
        interactions.Option(
            name="brief",
            description="간략하게 표시합니다.",
            type=interactions.OptionType.BOOLEAN
        )
    ]
)
async def PosterAt(ctx: interactions.CommandContext, pos: int, brief: bool = True):
    printl(f'(PosterAt) Called with state: {pos}')
    embed = interactions.Embed(
        title=f"게시 위치가 '{pos}'이고, 상태가 [posted, approved]인 포스터 목록",
        description="포스터 목록입니다.",
        color=0x00ff00
    )
    pp = Manager.GetPostersPosition(pos)
    pp.sort(key=lambda x: x["posttime"], reverse=False)
    if len(pp) == 0:
        embed.add_field(
            name="포스터가 없습니다.",
            value=":drooling_face:",
        )
    else:
        for p in pp:
            AddPosterEmbed(embed, p, brief)
    await ctx.send("", embeds=embed)




@bot.command(
    name="posttimechange",
    name_localizations={"ko": "시작시간변경"},
    description="포스터 시작 시간을 변경합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="timepost",
            description="변경할 포스터 시작 시간",
            type=interactions.OptionType.STRING,
            required=True
        ),
        interactions.Option(
            name="posterid",
            description="포스터 ID",
            type=interactions.OptionType.STRING
        )
    ]
)
async def ChangePosterPostTime(ctx: interactions.CommandContext, timepost: str, posterid: str = None):
    if posterid is None:
        posterid = str(ctx.channel_id)
    printl(f'(PosterStartTime) Ticket Id: {posterid}, Time: {timepost}')
    timepost = timepost.replace(";", ":")
    timepost = ParseTimeInput(timepost)
    if timepost is None:
        embed = interactions.Embed(
            title="포스터 시작 시간 변경",
            description=f"포스터 {posterid}의 시작 시간 변경에 실패했습니다.",
            color=0xff0000
        )
        await ctx.send("", embeds=embed)
        return
    
    st = Manager.ChangePosterPostTime(str(posterid), timepost)
    if st:
        embed = interactions.Embed(
            title="포스터 시작 시간 변경",
            description=f"포스터 {posterid}의 시작 시간이 {timepost}로 변경되었습니다.",
            color=0x00ff00
        )
    else:
        embed = interactions.Embed(
            title="포스터 시작 시간 변경",
            description=f"포스터 {posterid}의 시작 시간 변경에 실패했습니다.",
            color=0xff0000
        )
    await ctx.send("", embeds=embed)

@bot.command(
    name="endtimechange",
    name_localizations={"ko": "종료시간변경"},
    description="포스터 종료 시간을 변경합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="timepost",
            description="변경할 포스터 종료 시간",
            type=interactions.OptionType.STRING,
            required=True
        ),
        interactions.Option(
            name="posterid",
            description="포스터 ID",
            type=interactions.OptionType.STRING
        )
    ]
)
async def ChangePosterEndTime(ctx: interactions.CommandContext, timepost: str, posterid: str = None):
    if posterid is None:
        posterid = str(ctx.channel_id)
    printl(f'(PosterStartTime) Ticket Id: {posterid}, Time: {timepost}')
    timepost = timepost.replace(";", ":")
    timepost = ParseTimeInput(timepost)
    if timepost is None:
        embed = interactions.Embed(
            title="포스터 종료 시간 변경",
            description=f"포스터 {posterid}의 시작 시간 변경에 실패했습니다.",
            color=0xff0000
        )
        await ctx.send("", embeds=embed)
        return
    st = Manager.ChangePosterEndTime(str(posterid), timepost)
    if st:
        embed = interactions.Embed(
            title="포스터 종료 시간 변경",
            description=f"포스터 {posterid}의 종료 시간이 {timepost}로 변경되었습니다.",
            color=0x00ff00
        )
    else:
        embed = interactions.Embed(
            title="포스터 종료 시간 변경",
            description=f"포스터 {posterid}의 종료 시간 변경에 실패했습니다.",
            color=0xff0000
        )
    await ctx.send("", embeds=embed)

@bot.command(
    name="posterimagechange",
    name_localizations={"ko": "이미지변경"},
    description="포스터 이미지를 변경합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="url",
            description="변경할 이미지 url",
            type=interactions.OptionType.STRING,
            required=True
        ),
        interactions.Option(
            name="posterid",
            description="포스터 ID",
            type=interactions.OptionType.STRING
        )
    ]
)
async def ChangePosterImage(ctx: interactions.CommandContext, url: str, posterid: str = None):
    if posterid is None:
        posterid = str(ctx.channel_id)
    printl(f'(ChangePosterImage) Ticket Id: {posterid}, url: {url}')
    st = Manager.ChangePosterImage(str(posterid), url)
    if st:
        embed = interactions.Embed(
            title="포스터 이미지 변경",
            description=f"포스터 {posterid}의 이미지가 변경되었습니다.",
            color=0x00ff00
        )
    else:
        embed = interactions.Embed(
            title="포스터 이미지 변경",
            description=f"포스터 {posterid}의 이미지 변경에 실패했습니다.",
            color=0xff0000
        )
    await ctx.send("", embeds=embed)

@bot.command(
    name="posterpositionchange",
    name_localizations={"ko": "위치변경"},
    description="포스터 위치를 변경합니다.",
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    scope=GUILD,
    options = [
        interactions.Option(
            name="pos",
            description="변경할 포스터 위치",
            type=interactions.OptionType.INTEGER,
            required=True
        ),
        interactions.Option(
            name="posterid",
            description="포스터 ID",
            type=interactions.OptionType.STRING
        )
    ]
)
async def ChangePosterPosition(ctx: interactions.CommandContext, pos: int, posterid: str = None):
    if posterid is None:
        posterid = str(ctx.channel_id)
    printl(f'(ChangePosterPosition) Ticket Id: {posterid}, pos: {pos}')
    st = Manager.ChangePosterPosition(str(posterid), pos)
    if st:
        embed = interactions.Embed(
            title="포스터 위치 변경",
            description=f"포스터 {posterid}의 위치가 {pos}로 변경되었습니다.",
            color=0x00ff00
        )
    else:
        embed = interactions.Embed(
            title="포스터 위치 변경",
            description=f"포스터 {posterid}의 위치 변경에 실패했습니다.",
            color=0xff0000
        )
    await ctx.send("", embeds=embed)



@bot.command(
    name="status",
    name_localizations={"ko": "현황"},
    description="현재 포스터 게시 현황을 불러옵니다.",
    scope=GUILD,
    options = [
        interactions.Option(
            name="brief",
            description="간략하게 표시합니다.",
            type=interactions.OptionType.BOOLEAN
        )
    ]
)
async def PosterStatus(ctx: interactions.CommandContext, brief: bool = True):
    printl(f'(PosterStatus) Called')
    # Force Brief Expression
    brief = True
    embed = interactions.Embed(
        title="게시 중인, 게시 예정 포스터 목록 및 현황",
        description="매 시 정각에 업데이트 됩니다.",
        color=0xffffff
    )
    for ind in range(1, 7):
        pps = Manager.GetPostersPosition(ind)
        pps.sort(key=lambda x: x["posttime"], reverse=False)
        if len(pps) == 0:
            embed.add_field(
                name=f"포스터 {ind}",
                value="게시 중인 포스터 없음. :cry: ",
                inline=False
            )
        else:
            txt = ""
            tlt = "`게시중인 포스터 없음`"
            if pps[0]["state"] == "posted":
                tstart = pps[0]["posttime"]
                tend = pps[0]["endtime"]
                pid = pps[0]["formId"]
                tlt = f"**`게시중`** - <#{pid}> {HumanTime(tstart)} ~ {HumanTime(tend)}\n"
                if len(pps) > 1:
                    txt += "`게시 예정`\n"
                    for iv in range(1, len(pps)):
                        txt += f"<#{pps[iv]['formId']}> {HumanTime(pps[iv]['posttime'])} ~ {HumanTime(pps[iv]['endtime'])}\n"
            else:
                txt += "`게시 예정`\n"
                txt += f"<#{pps[0]['formId']}> {HumanTime(pps[0]['posttime'])} ~ {HumanTime(pps[0]['endtime'])}\n"
            embed.add_field(
                name=f"위치 {ind} {tlt}",
                value= txt,
                inline=False
            )
    pps = Manager.GetPostersInfo("pending")
    embed.add_field(
        name="승인 대기를 기다리는 포스터",
        value=f"{len(pps)}개",
        inline=False
    )
    await ctx.send("", embeds=embed)




bot.start()
