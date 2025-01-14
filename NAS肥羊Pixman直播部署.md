FinalShell

sudo -i

http://192.168.0.2:5050/tptv_proxy.m3u?server=192.168.0.2:8000

方式运行，不过是allinone的指令了：

docker run -d --restart unless-stopped --net=host --privileged=true -p 35455:35455 --name allinone youshandefeiyang/allinone

配置watchtower每天凌晨两点自动监听allinone镜像更新：

docker run -d --name watchtower --restart unless-stopped -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower allinone -c --schedule "0 0 2 * * *"



IPTV ofiii直播镜像，小白专属 沐晨大佬提供

docker镜像拉取: docker pull doubebly/doube-ofiii:latest

docker镜像运行: docker run -d --name=doube-ofiii -p 50002:5000 --restart=always doubebly/doube-ofiii:latest

## 构建完成后查看项目详细数据，使用 http://群晖ip:5050/tptv_proxy.m3u?server=群晖ip:8000 即可订阅 TPTV 直播源，其他同理。

访问 http://ip:port/help (示例：http://127.0.0.1:50002/help)，可以看到txt和m3u的订阅链接


IPTV直播 
http://192.168.0.2:35455/tv.m3u
http://192.168.0.2:35455/mytvsuper.m3u


# 「Pixman」自动化部署 -更新（11.21）

Pixman 脚本 SSH 执行代码：
bash -c "$(curl -sL https://yang-1989.eu.org/pixman.sh)"
备用地址：
bash -c "$(curl -sL https://raw.githubusercontent.com/YanG-1989/m3u/refs/heads/main/Pixman.sh)"

脚本功能：
简化直播搭建流程，提供一站式解决方案，y 键 即可启动。
1. 一键部署 Pixman：支持自定义参数，自动检测Docker环境，自动反向代理设置，myTV 订阅转换设置，确保用户在不同网络条件下的最佳体验。
2. 一键部署 Allinone：支持 IPTV 启停功能，Docker Compose、av3a 助手 安装等功能，满足用户的多样化需求，轻松搭建全面的直播解决方案。
3. 全面的功能支持：内置 o11、3x-ui 、sing-box 、Sub Store 及 1Panel 管理面板，集成强大的工具箱，提升用户操作的灵活性和便捷性。
4. 定时任务与自动更新：根据网络环境设置不同的定时任务，进行自动检查和更新容器版本，提供独立的 Watchtower 设置功能，确保用户始终使用最新版本。
5. 增强兼容性与优化：优化代码逻辑，支持软路由环境，简化操作流程，确保在不同网络条件下稳定运行，并定期修复潜在BUG，欢迎用户反馈问题。



◆ 订阅地址：
■ 央视频 YSP :  http://192.168.0.2:52055/ysp.m3u
■ 江苏移动魔百盒 TPTV : http://192.168.0.2:52055/tptv.m3u 或 http://192.168.0.2:52055/tptv_proxy.m3u
■ 中国移动 iTV : http://192.168.0.2:52055/itv.m3u 或 http://192.168.0.2:52055/itv_proxy.m3u
■ Beesport : http://192.168.0.2:52055/beesport.m3u
■ TheTV : http://192.168.0.2:52055/thetv.m3u
■ DLHD : http://192.168.0.2:52055/dlhd.m3u
---------------------------------------------------------
---  Pixman 详细使用说明: https://pixman.io/topics/17  ---
---  Pixman.sh 脚本日志: https://pixman.io/topics/142  ---
---------------------------------------------------------


◆ 订阅地址：
■ TV 集合 : http://192.168.0.2:35455/tv.m3u
■ TPTV : http://192.168.0.2:35455/tptv.m3u
■ YY轮播 : http://192.168.0.2:35455/yylunbo.m3u
■ BiliBili生活 : http://192.168.0.2:35455/bililive.m3u
■ 虎牙一起看 : http://192.168.0.2:35455/huyayqk.m3u
■ 斗鱼一起看 : http://192.168.0.2:35455/douyuyqk.m3u
---------------------------------------------------------
■ 代理地址：
■ BiliBili 代理 : http://192.168.0.2:35455/bilibili/{VIDEO_ID}
■ 虎牙 代理 : http://192.168.0.2:35455/huya/{VIDEO_ID}
■ 斗鱼 代理 : http://192.168.0.2:35455/douyu/{VIDEO_ID}
■ YY 代理 : http://192.168.0.2:35455/yy/{VIDEO_ID}
■ 抖音 代理 : http://192.168.0.2:35455/douyin/{VIDEO_ID}
■ YouTube 代理 : http://192.168.0.2:35455/youtube/{VIDEO_ID}
---------------------------------------------------------
---    allinone 详细使用说明: https://yycx.eu.org      ---
---  Pixman.sh 脚本日志: https://pixman.io/topics/142  ---
---------------------------------------------------------
