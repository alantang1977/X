# 配置文件，包含直播源URL、黑名单URL、公告信息、EPG URL、测速超时时间和线程池最大工作线程数

# 优先使用的IP版本，这里设置为ipv4或ipv6
ip_version_priority = "ipv4"

# 直播源URL列表
source_urls = [
    "https://gitee.com/t-v/tt/raw/t/c.txt",
    "http://kkk.888.3116598.xyz/user/HKTV.txt",
    "http://gg.7749.org/z/i/gdss.txt",
    "http://is.is-great.org/ii/1749383140.txt",
    "https://live.kakaxi-1.ink/ipv4.txt",
    "https://live.kakaxi-1.ink/ipv4.1.txt",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/myTV.txt",
    "https://git.acwing.com/cisenyuan/kdsb/-/raw/main/txt/tvzb.txt",
    "https://yk95.yymmiptv.top",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/中国IPTV",
    "https://www.iyouhun.com/tv/myIPTV/ipv6.m3u",
    "https://www.iyouhun.com/tv/myIPTV/ipv4.m3u",
    "http://rihou.cc:555/gggg.nzk",
    "https://live.izbds.com/tv/iptv4.txt",
    "http://47.120.41.246:8899/zb.txt",
    "http://live.nctv.top/x.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/iptv_api/refs/heads/main/output/live_ipv4.m3u",
    "https://live.izbds.com/tv/iptv4.txt",
    "http://47.120.41.246:8899/zb.txt",
    "http://1.94.31.214/live/livelite.txt",
    "https://web.banye.tech:7777/tvbus/yogurtTv.txt",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/go.txt",
    "https://smart.pendy.dpdns.org/m3u/Smart.m3u",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/咪咕直播",
    "http://zhibo.feylen.top/fltv/js/ku9live.php?tpye=fl.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/Alan-Alana/IPTV/refs/heads/main/channl.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/peterHchina/iptv/refs/heads/main/IPTV-V4.m3u",
    "https://iptv.catvod.com/tv.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/hostemail/cdn/main/live/tv.txt",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/JunTV/refs/heads/main/output/result.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/ssili126/tv/main/itvlist.m3u",
    "https://live.zbds.top/tv/iptv4.txt",
    "https://gitee.com/xxy002/zhiboyuan/raw/master/dsy",  
    "https://live.zbds.top/tv/iptv6.txt",
    "http://home.jundie.top:81/Cat/tv/live.txt",
    "https://live.fanmingming.cn/tv/m3u/ipv6.m3u",
    "https://live.zhoujie218.top/tv/iptv6.txt",
    "https://cdn.jsdelivr.net/gh/YueChan/live@main/IPTV.m3u",
    "https://fm1077.serv00.net/SmartTV.m3u",
    "https://cnb.cool/junchao.tang/llive/-/git/raw/main/Gather.m3u",
    "https://m3u.ibert.me/txt/o_cn.txt",
    "https://m3u.ibert.me/txt/j_iptv.txt",
    "https://iptv.b2og.com/txt/fmml_ipv6.txt",   
    "https://live.zhoujie218.top/tv/iptv4.txt"
]

# 直播源黑名单URL列表，去除了重复项
url_blacklist = [
    "epg.pw/stream/",
    "103.40.13.71:12390",
    "[2409:8087:1a01:df::4077]/PLTV/",
    "http://[2409:8087:1a01:df::7005]:80/ottrrs.hl.chinamobile.com/PLTV/88888888/224/3221226419/index.m3u8",
    "http://[2409:8087:5e00:24::1e]:6060/000000001000/1000000006000233001/1.m3u8",
    "8.210.140.75:68",
    "154.12.50.54",
    "yinhe.live_hls.zte.com",
    "8.137.59.151",
    "[2409:8087:7000:20:1000::22]:6060",
    "histar.zapi.us.kg",
    "www.tfiplaytv.vip",
    "dp.sxtv.top",
    "111.230.30.193",
    "148.135.93.213:81",
    "live.goodiptv.club",
    "iptv.luas.edu.cn",
    "[2409:8087:2001:20:2800:0:df6e:eb22]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb23]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb1d]/ott.mobaibox.com/",
    "[2409:8087:2001:20:2800:0:df6e:eb1d]:80",
    "[2409:8087:2001:20:2800:0:df6e:eb24]",
    "2409:8087:2001:20:2800:0:df6e:eb25]:80",
    "stream1.freetv.fun",
    "chinamobile",
    "gaoma",
    "[2409:8087:2001:20:2800:0:df6e:eb27]"
]

# 公告信息
announcements = [
    {
        "channel": "更新日期",
        "entries": [
            {
                "name": None,
                "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/X/main/Pictures/Robot.mp4",
                "logo": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/X/main/Pictures/SuperMAN.png"
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
