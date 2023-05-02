from steamid_converter import Converter
from bs4 import BeautifulSoup
import customtkinter as ctk
from io import BytesIO
from PIL import Image
import cloudscraper
import telnetlib
import winsound
import requests
import json
import os
import re
os.system('cls')

class RankRevealApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.host = "127.0.0.1"
        self.port = 2121
        self.title('Rank Reveal')
        self.config(bg='#565B5E')
        self.rank_reveal()
        self.resizable(0, 0)

    def scraper_info(self, id64):
        try:
            url = f"https://csgostats.gg/player/{id64}"
            flag = False

            while not flag:
                try:
                    sc = cloudscraper.create_scraper()
                    html_text = sc.get(url).text
                    flag = True
                except:
                    continue
                
            p = re.compile('var stats = .*')
            soup = BeautifulSoup(html_text, 'lxml')

            name = soup.find('div', id='player-name')
            scripts = soup.find_all('script')
            data = ''

            for script in scripts:
                try:
                    m = p.match(script.string.strip())
                    if m:
                        data = m.group()
                        break
                except:
                    continue

            data_json = json.loads(data[12:-1])
            data_json['player_name'] = name.text
            return data_json
        except:
            return None

    def scrap_profile_image(self, id64):
        try:
            url = f"https://steamcommunity.com/profiles/{id64}"
            flag = False

            while not flag:
                try:
                    sc = cloudscraper.create_scraper()
                    html_text = sc.get(url).text
                    flag = True
                except:
                    continue
                
            soup = BeautifulSoup(html_text, 'html.parser')

            profile_image_link = str(soup.find("div", {"class":"playerAvatarAutoSizeInner"})).split('\n')[-2].replace('<img src="', '').replace('"/>', '')

            return profile_image_link
        except:
            return 'https://steamuserimages-a.akamaihd.net/ugc/868480752636433334/1D2881C5C9B3AD28A1D8852903A8F9E1FF45C2C8/'

    def scrap_faceit(self, id64):
        try:
            url = f"https://faceitfinder.com/profile/{id64}"

            flag = False

            while not flag:
                try:
                    sc = cloudscraper.create_scraper()
                    html_text = sc.get(url).text
                    flag = True
                except:
                    continue

            soup = BeautifulSoup(html_text, 'html.parser')

            faceit_level_link = str(soup.find("img", {"width":"48px", "height":"48px"})).split('_')[2]
            faceit_elo_link = str(soup.find("div", {"style":"width: 88px;", "class":"account-faceit-stats-single"}).find("strong")).replace('<strong>', '').replace('</strong>', '')

            return faceit_level_link, faceit_elo_link
        except:
            return None, ''

    def getPlayerRank(self, id64):
        data_json = self.scraper_info(id64)
        if data_json != None:
            curr_rank = data_json['rank']
            best_rank = data_json['best']['rank']
            comp_wins = data_json['comp_wins']
            win_rate = data_json['overall']['wr']
            headshot_rate = data_json['overall']['hs']
            kills_per_death = data_json['overall']['kpd'] 
            player = curr_rank, best_rank, comp_wins, win_rate, headshot_rate, kills_per_death
            return player
        return 'Error with ' + id64

    def get_players(self):
        def read_console(stop=[]):
            res = ""
            while True:
                data = tn.read_until(b"\n").decode("utf-8")
                res += data
                if not stop:
                    break
                line = data.strip()
                if type(stop) is list:
                    if line in stop:
                        break
                if type(stop) is str:
                    if line == stop:
                        break
            return res
        try:
            tn = telnetlib.Telnet(self.host, self.port)
        except:
            print(f"failed to connect to csgo (game not open? -netconport {self.port} not set?)")
            tn = None

        # get local name
        tn.write(b"name\n")
        name_res = read_console()
        local_name = name_res.split('" ( def')[0].split('name" = "')[1]

        # get status
        tn.write(b"status\n")
        status_res = read_console(["#end", "Not connected to server"])

        # parse result
        lines = status_res.split("\r\n")
        players = []
        for line in lines:
            if not line.startswith("# "):
                continue

            if line == "# userid name uniqueid connected ping loss state rate":
                continue

            line = line.split("#")[1]

            # parse fields
            fields = []
            cur_field = ""
            in_str = False
            in_space = True
            for char in line:
                if char == '"':
                    in_str = not in_str
                    continue

                if not in_str:
                    if char == " ":
                        if not in_space:
                            fields.append(cur_field)
                            cur_field = ""
                            in_space = True
                        continue

                cur_field += char
                in_space = False

            if cur_field:
                fields.append(cur_field)

            # filter out gotv
            if fields[1] in ["GOTV", "BOT"]:
                continue

            # add player
            player = {
                "userid": f"{fields[0]} {fields[1]}",
                "name": fields[2].replace('"', ""),
                "steamid": fields[3],
                "time_connected": fields[4],
                "ping": fields[5],
                "loss": fields[6],
                "state": fields[7],
                "rate": fields[8],
            }
            player["self"] = player["name"] == local_name
            players.append(player)
        return players

    def rank_reveal(self):
        players = self.get_players()
        column_list = list()
        column_list.append(['', 'Player', '     Rank', 'Best Rank', 'MM Wins', 'Win Rate', 'HS%', 'K/D', '    Faceit Elo', ''])

        if not players:
            print("no players in server")
            return
        for _, player in enumerate(players):
            if player["self"]:
                continue
            id64 = Converter.to_steamID64(player["steamid"])
            faceit_level_link, faceit_elo_link = self.scrap_faceit(id64)
            try:
                mm_rank, best_rank, comp_wins, win_rate, headshot_rate, kills_per_death = self.getPlayerRank(id64)
                column_list.append((self.scrap_profile_image(id64), player["name"], mm_rank, best_rank, comp_wins, f'{str(win_rate)}%', f'{str(headshot_rate)}%', kills_per_death, faceit_level_link, faceit_elo_link))
            except:
                column_list.append((self.scrap_profile_image(id64), player["name"], 0, 0, '', '', '', '', faceit_level_link, faceit_elo_link))

        for i in range(len(column_list)):
            for j in range(len(column_list[0])):
                    if j == 2 or j == 3:
                        if i == 0:
                            entry = ctk.CTkEntry(self, width=200/3 + 6, bg_color='#565B5E')
                            entry.grid(row=i, column=j)
                            entry.insert(ctk.END, column_list[i][j])
                            entry.configure(state='disabled')
                        else:
                            rank_image = ctk.CTkImage(Image.open(BytesIO(requests.get(f'https://static.csgostats.gg/images/ranks/{str(column_list[i][j])}.png').content)), size=(200/3, 80/3))
                            rank_label = ctk.CTkLabel(self, text='', image=rank_image, bg_color='#565B5E')
                            rank_label.grid(row=i, column=j)
                    elif j == 1:
                        if i != 0:
                            profile_image = ctk.CTkImage(Image.open(BytesIO(requests.get(column_list[i][j - 1]).content)), size=(80/3, 80/3))
                            profile_label = ctk.CTkLabel(self, text='', image=profile_image, bg_color='#565B5E')
                            profile_label.grid(row=i, column=j - 1)
                        if i == 0:
                            entry = ctk.CTkEntry(self, width=150 + 80/3, bg_color='#565B5E')
                            entry.grid(row=i, column=j - 1, columnspan=2)
                            entry.insert(ctk.END, column_list[i][j])
                            entry.configure(state='disabled')
                        else:
                            entry = ctk.CTkEntry(self, width=150, bg_color='#565B5E')
                            entry.grid(row=i, column=j)
                            entry.insert(ctk.END, column_list[i][j])
                            entry.configure(state='disabled')
                    elif j == 8:
                        if i == 0:
                            entry = ctk.CTkEntry(self, width=200/3 + 80/2.7, bg_color='#565B5E')
                            entry.grid(row=i, column=j, columnspan=2)
                            entry.insert(ctk.END, column_list[i][j])
                            entry.configure(state='disabled')
                        else:
                            if column_list[i][j] == None and column_list[i][j + 1] == '':
                                entry = ctk.CTkEntry(self, width=200/3 + 80/2.7, bg_color='#565B5E')
                                entry.grid(row=i, column=j, columnspan=2)
                                entry.insert(ctk.END, '')
                                entry.configure(state='disabled')
                            else:
                                faceit_level_image = ctk.CTkImage(Image.open(BytesIO(requests.get(f'https://faceitaccount.com/wp-content/themes/kadence/faceit/assets/ranks/skill_level_{column_list[i][j]}_lg.png').content)), size=(80/2.7, 80/2.7))
                                faceit_level_label = ctk.CTkLabel(self, text='', image=faceit_level_image, bg_color='#565B5E')
                                faceit_level_label.grid(row=i, column=j)
                                entry = ctk.CTkEntry(self, width=200/3, bg_color='#565B5E')
                                entry.grid(row=i, column=j + 1)
                                entry.insert(ctk.END, column_list[i][j + 1])
                                entry.configure(state='disabled')
                    else:
                        if j != 0 and j != 8 and j != 9:
                            entry = ctk.CTkEntry(self, width=200/3, bg_color='#565B5E')
                            entry.grid(row=i, column=j)
                            entry.insert(ctk.END, column_list[i][j])
                            entry.configure(state='disabled')
        winsound.Beep(1000, 500)

if __name__ == '__main__':
    rankreveal_app = RankRevealApp()
    rankreveal_app.mainloop()
