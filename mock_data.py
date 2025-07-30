# mock_data.py
import time

FAKE_SONGS = [
    # Existing data...
    {"id": 1, "name": "七里香", "artists": [{"name": "周杰伦"}], "album": {"name": "七里香", "picUrl": "http://p4.music.126.net/VnZiScyynLG7atLIZ2YPkw==/109951163941994697.jpg"}, "format": "mp3"},
    {"id": 2, "name": "晴天", "artists": [{"name": "周杰伦"}], "album": {"name": "叶惠美", "picUrl": "http://p4.music.126.net/VnZiScyynLG7atLIZ2YPkw==/109951163941994697.jpg"}, "format": "mp3"},
    {"id": 3, "name": "稻香", "artists": [{"name": "周杰伦"}], "album": {"name": "魔杰座", "picUrl": "http://p4.music.126.net/VnZiScyynLG7atLIZ2YPkw==/109951163941994697.jpg"}, "format": "mp3"},
    {"id": 4, "name": "夜曲", "artists": [{"name": "周杰伦"}], "album": {"name": "十一月的萧邦", "picUrl": "http://p4.music.126.net/VnZiScyynLG7atLIZ2YPkw==/109951163941994697.jpg"}, "format": "mp3"},
    {"id": 5, "name": "以父之名", "artists": [{"name": "周杰伦"}], "album": {"name": "叶惠美", "picUrl": "http://p4.music.126.net/VnZiScyynLG7atLIZ2YPkw==/109951163941994697.jpg"}, "format": "mp3"},
    {"id": 6, "name": "浮夸", "artists": [{"name": "陈奕迅"}], "album": {"name": "U87", "picUrl": "http://p3.music.126.net/e_n__q4Yf4s4-PA2Fb0pMg==/109951163391216892.jpg"}, "format": "mp3"},
    {"id": 7, "name": "十年", "artists": [{"name": "陈奕迅"}], "album": {"name": "黑白灰", "picUrl": "http://p3.music.126.net/e_n__q4Yf4s4-PA2Fb0pMg==/109951163391216892.jpg"}, "format": "mp3"},
    {"id": 8, "name": "爱情转移", "artists": [{"name": "陈奕迅"}], "album": {"name": "认了吧", "picUrl": "http://p3.music.126.net/e_n__q4Yf4s4-PA2Fb0pMg==/109951163391216892.jpg"}, "format": "mp3"},
    {"id": 9, "name": "红玫瑰", "artists": [{"name": "陈奕迅"}], "album": {"name": "认了吧", "picUrl": "http://p3.music.126.net/e_n__q4Yf4s4-PA2Fb0pMg==/109951163391216892.jpg"}, "format": "mp3"},
    {"id": 10, "name": "K歌之王", "artists": [{"name": "陈奕迅"}], "album": {"name": "反正是我", "picUrl": "http://p3.music.126.net/e_n__q4Yf4s4-PA2Fb0pMg==/109951163391216892.jpg"}, "format": "mp3"},
    {"id": 11, "name": "喜欢你", "artists": [{"name": "G.E.M.邓紫棋"}], "album": {"name": "喜欢你", "picUrl": "http://p4.music.126.net/l_j_V_bsI9pB_c_V9b5g==/109951163001838290.jpg"}, "format": "mp3"},
    {"id": 12, "name": "光年之外", "artists": [{"name": "G.E.M.邓紫棋"}], "album": {"name": "光年之外", "picUrl": "http://p4.music.126.net/l_j_V_bsI9pB_c_V9b5g==/109951163001838290.jpg"}, "format": "mp3"},

    # New data from JSON
    {"id": 13, "name": "好心分手", "artists": [{"name": "卢巧音"}, {"name": "王力宏"}], "album": {"name": "不能不爱…卢巧音精选", "picUrl": "https://p3.music.126.net/PNNb7OIbiHY7cy9i9rDxyw==/109951165994496224.jpg"}, "format": "flac"},
    {"id": 14, "name": "恰似你的温柔", "artists": [{"name": "蔡琴"}], "album": {"name": "精选‧蔡琴", "picUrl": "https://p3.music.126.net/MDJy_P_2q_nbPedh5kVuUg==/109951169217344003.jpg"}, "format": "flac"},
    {"id": 15, "name": "情非得已 (童声版)", "artists": [{"name": "群星"}], "album": {"name": "热门华语275", "picUrl": "https://p3.music.126.net/cpoUinrExafBHL5Nv5iDHQ==/109951166361218466.jpg"}, "format": "mp3"}
]

