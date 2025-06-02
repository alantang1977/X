# 直播源URL列表（建议去重）
source_urls = [
    "https://yk95.yymmiptv.top",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/中国IPTV",
    "https://www.iyouhun.com/tv/myIPTV/ipv6.m3u",
    "https://www.iyouhun.com/tv/myIPTV/ipv4.m3u",
    "http://rihou.cc:555/gggg.nzk",
    "https://live.izbds.com/tv/iptv4.txt",
    "http://47.120.41.246:8899/zb.txt",
    "http://live.nctv.top/x.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/iptv_api/refs/heads/main/output/live_ipv4.m3u",
    "http://1.94.31.214/live/livelite.txt",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/go.txt", 
    "https://smart.pendy.dpdns.org/m3u/Smart.m3u",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/咪咕直播",
    "http://zhibo.feylen.top/fltv/js/ku9live.php?tpye=fl.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/Alan-Alana/IPTV/refs/heads/main/channl.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/peterHchina/iptv/refs/heads/main/IPTV-V4.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/peterHchina/iptv/refs/heads/main/IPTV-V6.m3u",
    "http://lisha521.dynv6.net.fh4u.org/tv.txt",
    "https://iptv.catvod.com/tv.m3u",
    "https://live.zbds.top/tv/iptv4.txt",
    "https://gitee.com/xxy002/zhiboyuan/raw/master/dsy",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/big-mouth-cn/tv/main/iptv-ok.m3u",
    "https://codeberg.org/alfredisme/mytvsources/raw/branch/main/mylist-ipv6.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/lalifeier/IPTV/main/m3u/IPTV.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/wwb521/live/main/tv.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv6.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/YueChan/Live/refs/heads/main/APTV.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/Kimentanm/aptv/master/m3u/iptv.m3u",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/Guovin/TV/gd/output/result.txt",
    "http://home.jundie.top:81/Cat/tv/live.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/vbskycn/iptv/master/tv/hd.txt",
    "https://live.fanmingming.cn/tv/m3u/ipv6.m3u",
    "https://live.zhoujie218.top/tv/iptv6.txt",
    "https://cdn.jsdelivr.net/gh/YueChan/live@main/IPTV.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/cymz6/AutoIPTV-Hotel/main/lives.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/PizazzGY/TVBox_warehouse/main/live.txt",
    "https://fm1077.serv00.net/SmartTV.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.m3u",
    "https://live.zhoujie218.top/tv/iptv4.txt"
]

# 黑名单，禁止采集的部分URL片段（去重，不要覆盖为空）
url_blacklist = [
    "epg.pw/stream/", "103.40.13.71:12390", "[2409:8087:1a01:df::4077]/PLTV/",
    "http://[2409:8087:1a01:df::7005]:80/ottrrs.hl.chinamobile.com/PLTV/88888888/224/3221226419/index.m3u8",
    "http://[2409:8087:5e00:24::1e]:6060/000000001000/1000000006000233001/1.m3u8",
    "8.210.140.75:68", "154.12.50.54", "yinhe.live_hls.zte.com", "8.137.59.151",
    "[2409:8087:7000:20:1000::22]:6060", "histar.zapi.us.kg", "www.tfiplaytv.vip",
    "dp.sxtv.top", "111.230.30.193", "148.135.93.213:81", "live.goodiptv.club",
    "iptv.luas.edu.cn", "[2409:8087:2001:20:2800:0:df6e:eb22]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb23]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb1d]/ott.mobaibox.com/",
    "[2409:8087:2001:20:2800:0:df6e:eb1d]:80", "[2409:8087:2001:20:2800:0:df6e:eb24]",
    "2409:8087:2001:20:2800:0:df6e:eb25]:80", "stream1.freetv.fun", "chinamobile",
    "gaoma", "[2409:8087:2001:20:2800:0:df6e:eb27]"
]

# 公告频道
announcements = [
    {
        "channel": "更新日期",
        "entries": [
            {
                "name": None,
                "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/X/main/Pictures/Robot.mp4",
                "logo": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/X/main/Pictures/chao-assets.png"
            }
        ]
    }
]

# EPG（电子节目指南）URL列表
epg_urls = [
    "https://epg.v1.mk/fy.xml",
    "http://epg.51zmt.top:8000/e.xml",
    "https://epg.pw/xmltv/epg_CN.xml",
    "https://epg.pw/xmltv/epg_HK.xml",
    "https://epg.pw/xmltv/epg_TW.xml"
]
ip_version_priority = "ipv4"
