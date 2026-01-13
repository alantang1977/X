/**
 * 央视频 720P
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2026-1-2 02:46:31
 * 发布页 https://m.yangshipin.cn/
 * @config
 * debug: true
 * blockList: *.[ico|png|jpeg|jpg|gif|webp]*|*.css
 */

const baseUrl = 'https://m.yangshipin.cn/';
const headers = {
	'user-agent': 'Mozilla/5.0 (Linux; Android 12; HarmonyOS; ELS-AN10; HMSCore 6.11.0.302) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 HuaweiBrowser/13.0.3.320 Mobile Safari/537.36'
};

/**
 * 初始化配置
 */
async function init(cfg) {
    return {};
}

/**
 * 首页分类
 */
async function homeContent(filter) {
    return {
        class: [
            { type_id: "1", type_name: "央视" },
            { type_id: "2", type_name: "卫视" }
        ]
    };
}

/**
 * 首页推荐视频
 */
async function homeVideoContent() {
    return { list: [] };
}

/**
 * 分类内容
 */
async function categoryContent(tid, pg, filter, extend) {
    const res = await Java.req('https://h5access.yangshipin.cn/web/tv_web_share?raw=1&pid=600002485');
    const jsonData = JSON.parse(res.body);
    const pidInfo = jsonData?.data?.pidInfo || [];

    const isCentralTV = (name) => name.startsWith('CCTV') || name.startsWith('CGTN');

    const vods = pidInfo
        .filter(item => {
            if (item.vipInfo?.isVip !== false) return false;
            if (!item.pid || !item.channelName) return false;
            const isCentral = isCentralTV(item.channelName);
            return tid === '1' ? isCentral : !isCentral;
        })
        .map(item => {
            const isCentral = isCentralTV(item.channelName);
            const vodPic = item.audioPosterUrl;
            return {
                vod_id: item.pid,
                vod_name: item.channelName,
                vod_pic: vodPic,
                style: { type: "rect", ratio: isCentral ? 1.66 : 1 }
            };
        })
        .filter(item => item.vod_pic);
    
    return {
        code: 1,
        msg: "数据列表",
        list: vods,
        page: 1,
        pagecount: 1,
        limit: vods.length,
        total: vods.length
    };
}

/**
 * 详情页
 */
async function detailContent(ids) {
    const res = await Java.req(`https://h5access.yangshipin.cn/web/h5_live_poll?raw=1&pid=${ids[0]}&reqType=2`);
    const jsonData = JSON.parse(res.body);
    const epgs = jsonData?.data?.h5TVLivePollRsp?.tvLivePollRsp?.programs || [];
    const currentTime = jsonData?.data?.h5TVLivePollRsp?.tvLivePollRsp?.currentServerTime || 0;
    
    const dayStart = Math.floor(currentTime / 86400) * 86400;
    let liveName = '';
    let replayList = [];

    epgs.forEach(item => {
        const endTime = item.start_time_stamp + item.duration;
        if (currentTime >= item.start_time_stamp && currentTime <= endTime) {
            liveName = item.name;
        }
        if (item.start_time_stamp >= dayStart && item.start_time_stamp < currentTime) {
			let epg_time = formatTime(item.start_time_stamp, 'MM-DD HH:mm');
            replayList.push(`[${epg_time}]${item.name}$${ids[0]}_${item.start_time_stamp}_${item.id}`);
        }
    });

    const list = [{
        vod_id: ids[0],
        vod_name: jsonData?.data?.h5TVLivePollRsp?.tvLivePollRsp?.title,
        vod_content: jsonData?.data?.h5TVLivePollRsp?.tvLivePollRsp?.title + `【${liveName}】正在直播中 `,
        vod_play_from: '正在直播$$$节目回看',
        vod_play_url: `${liveName}$${ids[0]}$$$${replayList.join('#')}`
    }];
    return { code: 1, msg: "数据列表", page: 1, pagecount: 1, limit: 1, total: 1, list };
}

/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
    return { list: [] };
}

/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
	// Java.showWebView();
	let playUrl = `https://m.yangshipin.cn/tv?pid=${id}&ptag=4_1.0.5.15187_copy,4_1.0.0.20034_copy`;
	if (flag == '节目回看') {
		const ids = id.split("_"); 
		const res = await Java.req(`https://h5access.yangshipin.cn/web/h5_share?vappid=&vsecret=b42702bf7309a179d102f3d51b1add2fda0bc7ada64cb801&raw=1&shareToType=1&shareId=itemtype%3Dcommon%26shareType%3Dtv%26pid%3D${ids[0]}%26startTime%3D${ids[1]}%26programID%3D${ids[2]}&shareFrom=h5`);
		const jsonData = JSON.parse(res.body);
		playUrl = jsonData.data.shareUrl;
	}
    return {
        type: 'sniff',
        url: playUrl,
		headers: headers,
        script: `let t=setInterval(()=>{let p=document.querySelector("#v-live-video");if(p?.play){p.play();clearInterval(t)}},100);`,
        timeout: 15
    };
}


function formatTime(timestamp, format = 'YYYY-MM-DD HH:mm:ss') {
    const date = new Date(timestamp * 1000);
    const map = {
        'YYYY': date.getFullYear(),
        'MM': String(date.getMonth() + 1).padStart(2, '0'),
        'DD': String(date.getDate()).padStart(2, '0'),
        'HH': String(date.getHours()).padStart(2, '0'),
        'mm': String(date.getMinutes()).padStart(2, '0'),
        'ss': String(date.getSeconds()).padStart(2, '0')
    };
    
    return format.replace(/YYYY|MM|DD|HH|mm|ss/g, matched => map[matched]);
}

