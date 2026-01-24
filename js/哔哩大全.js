const axios = require("axios");

// ==========================================
//          配置区 - 请按需填写
// ==========================================
const BILI_COOKIE = "";

const BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Cookie": BILI_COOKIE
};

const isLoggedIn = () => BILI_COOKIE && BILI_COOKIE.includes("SESSDATA=");

// ==========================================
//          核心工具：Request Info 解析
// ==========================================
function getRequestInfo(req) {
    const headers = req.headers || {};
    // 优先读取 Host，如果没有则兜底 127.0.0.1:9978 (OKHttp 默认端口)
    const host = headers['host'] || headers['Host'] || '127.0.0.1:9978';
    const protocol = headers['x-forwarded-proto'] || 'http';
    const userAgent = headers['user-agent'] || headers['User-Agent'] || "";
    
    return {
        fullUrl: `${protocol}://${host}`,
        userAgent: userAgent
    };
}

// ==========================================
//          核心工具：MPD XML 生成器 (无依赖版)
// ==========================================
const escapeXml = (unsafe) => {
    if (!unsafe) return "";
    return unsafe.replace(/&/g, '&amp;')
                 .replace(/</g, '&lt;')
                 .replace(/>/g, '&gt;')
                 .replace(/"/g, '&quot;')
                 .replace(/'/g, '&apos;');
};

const getMpd = (dash) => {
    const duration = dash.duration ? `PT${dash.duration}S` : "PT0S";
    const minBufferTime = 'PT1.5S';
    
    let xml = `<?xml version="1.0" encoding="UTF-8"?>`;
    xml += `<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" type="static" minBufferTime="${minBufferTime}" mediaPresentationDuration="${duration}">`;
    xml += `<Period>`;

    // --- 视频轨道 ---
    if (dash.video) {
        const bestVideo = dash.video.sort((a, b) => {
            // 优先级1: 画质 ID (120=4K > 116=1080P60 > 80=1080P)
            if (b.id !== a.id) return b.id - a.id;
            // 优先级2: 码率 (Bandwidth)
            return (b.bandwidth || 0) - (a.bandwidth || 0);
        })[0];

        if (bestVideo) {
            xml += `<AdaptationSet mimeType="video/mp4" contentType="video" subsegmentAlignment="true" subsegmentStartsWithSAP="1">`;
            // codecs 自动回填，如果是 HEVC 会显示 hev1...
            xml += `<Representation id="${bestVideo.id}" codecs="${bestVideo.codecs || 'avc1.64001E'}" bandwidth="${bestVideo.bandwidth}" width="${bestVideo.width}" height="${bestVideo.height}" frameRate="${bestVideo.frame_rate}">`;
            
            let baseUrl = bestVideo.baseUrl || bestVideo.base_url;
            xml += `<BaseURL>${escapeXml(baseUrl)}</BaseURL>`;
            
            if (bestVideo.SegmentBase?.Initialization) {
                xml += `<SegmentBase indexRange="${bestVideo.SegmentBase.indexRange}">`;
                xml += `<Initialization range="${bestVideo.SegmentBase.Initialization}"/>`;
                xml += `</SegmentBase>`;
            }
            xml += `</Representation></AdaptationSet>`;
        }
    }

    // --- 音频轨道 ---
    if (dash.audio && dash.audio.length > 0) {
        const audio = dash.audio[0];
        xml += `<AdaptationSet mimeType="audio/mp4" contentType="audio" subsegmentAlignment="true" subsegmentStartsWithSAP="1">`;
        xml += `<Representation id="${audio.id}" codecs="${audio.codecs || 'mp4a.40.2'}" bandwidth="${audio.bandwidth}">`;
        
        let baseUrl = audio.baseUrl || audio.base_url;
        xml += `<BaseURL>${escapeXml(baseUrl)}</BaseURL>`;
        
        if (audio.SegmentBase?.Initialization) {
            xml += `<SegmentBase indexRange="${audio.SegmentBase.indexRange}">`;
            xml += `<Initialization range="${audio.SegmentBase.Initialization}"/>`;
            xml += `</SegmentBase>`;
        }
        xml += `</Representation></AdaptationSet>`;
    }

    xml += `</Period></MPD>`;
    return xml;
};

// ==========================================
//          基础工具
// ==========================================
const fixCover = (url) => {
    if (!url) return "";
    if (url.startsWith("//")) return "https:" + url;
    return url;
};

const formatDuration = (seconds) => {
    if (seconds <= 0) return '00:00';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const formatSearchDuration = (duration) => {
    const parts = duration.split(':');
    if (parts.length === 2) return duration;
    return '00:00';
};

// ==========================================
//          分类定义
// ==========================================
const CLASSES = [
    { type_id: "演唱会", type_name: "演唱会" },
    { type_id: "粤语歌曲", type_name: "粤语" },
    { type_id: "2024年热门歌曲", type_name: "2024年热榜" },
    { type_id: "KTV热门歌曲", type_name: "KTV热门" },
    { type_id: "滚石歌曲", type_name: "滚石经典" },
    { type_id: "经典老歌", type_name: "经典老歌" },
    { type_id: "古风歌曲", type_name: "古风歌曲" },
    { type_id: "闽南语歌曲", type_name: "闽南语歌曲" },
    { type_id: "DJ歌曲", type_name: "DJ" },
    { type_id: "网红翻唱歌曲", type_name: "网红翻唱" },
    { type_id: "韩国女团演唱会", type_name: "韩国女团" },
    { type_id: "沙雕仙逆", type_name: "傻屌仙逆" },
    { type_id: "沙雕动画", type_name: "沙雕动画" },
    { type_id: "纪录片超清", type_name: "纪录片" },
    { type_id: "美食超清", type_name: "美食" },
    { type_id: "食谱", type_name: "食谱" },
    { type_id: "体育超清", type_name: "体育" },
    { type_id: "球星", type_name: "球星" },
    { type_id: "中小学教育", type_name: "教育" },
    { type_id: "幼儿教育", type_name: "幼儿教育" },
    { type_id: "旅游", type_name: "旅游" },
    { type_id: "风景4K", type_name: "风景" },
    { type_id: "说案", type_name: "说案" },
    { type_id: "知名UP主", type_name: "知名UP主" },
    { type_id: "探索发现超清", type_name: "探索发现" },
    { type_id: "鬼畜", type_name: "鬼畜" },
    { type_id: "搞笑超清", type_name: "搞笑" },
    { type_id: "儿童超清", type_name: "儿童" },
    { type_id: "动物世界超清", type_name: "动物世界" },
    { type_id: "相声小品超清", type_name: "相声小品" },
    { type_id: "戏曲", type_name: "戏曲" },
    { type_id: "解说", type_name: "解说" },
    { type_id: "演讲", type_name: "演讲" },
    { type_id: "小姐姐超清", type_name: "小姐姐" },
    { type_id: "荒野求生超清", type_name: "荒野求生" },
    { type_id: "健身", type_name: "健身" },
    { type_id: "帕梅拉", type_name: "帕梅拉" },
    { type_id: "太极拳", type_name: "太极拳" },
    { type_id: "广场舞", type_name: "广场舞" },
    { type_id: "舞蹈", type_name: "舞蹈" },
    { type_id: "4K", type_name: "4K" },
    { type_id: "电影", type_name: "电影" },
    { type_id: "电视剧", type_name: "电视剧" },
    { type_id: "白噪音超清", type_name: "白噪音" },
    { type_id: "考公考证", type_name: "考公考证" },
    { type_id: "平面设计教学", type_name: "平面设计教学" },
    { type_id: "软件教程", type_name: "软件教程" },
    { type_id: "Windows", type_name: "Windows" }
];

const FILTERS = {
    "演唱会": [
        { "key": "order", "name": "排序", "value": [{ "n": "综合排序", "v": "0" }, { "n": "最多点击", "v": "click" }, { "n": "最新发布", "v": "pubdate" }, { "n": "最多弹幕", "v": "dm" }, { "n": "最多收藏", "v": "stow" }] },
        { "key": "tid", "name": "分类", "value": [{ "n": "全部", "v": "演唱会4K" }, { "n": "A阿杜", "v": "阿杜演唱会4K" }, { "n": "A阿黛尔", "v": "阿黛尔演唱会4K" }, { "n": "BBeyond", "v": "Beyond演唱会4K" }, { "n": "BBy2", "v": "By2演唱会4K" }, { "n": "BBIGBANG", "v": "BIGBANG演唱会4K" }, { "n": "B布兰妮", "v": "布兰妮演唱会4K" }, { "n": "C程响", "v": "程响演唱会4K" }, { "n": "C陈奕迅", "v": "陈奕迅演唱会4K" }, { "n": "C蔡依林", "v": "蔡依林演唱会4K" }, { "n": "C初音未来", "v": "初音未来演唱会4K" }, { "n": "C蔡健雅", "v": "蔡健雅演唱会4K" }, { "n": "C陈小春", "v": "陈小春演唱会4K" }, { "n": "C草蜢", "v": "草蜢演唱会4K" }, { "n": "C陈慧娴", "v": "陈慧娴演唱会4K" }, { "n": "C崔健", "v": "崔健演唱会4K" }, { "n": "C仓木麻衣", "v": "仓木麻衣演唱会4K" }, { "n": "D戴荃", "v": "戴荃演唱会4K" }, { "n": "D动力火车", "v": "动力火车演唱会4K" }, { "n": "D邓丽君", "v": "邓丽君演唱会4K" }, { "n": "D丁当", "v": "丁当演唱会4K" }, { "n": "D刀郎", "v": "刀郎演唱会4K" }, { "n": "D邓紫棋", "v": "邓紫棋演唱会4K" }, { "n": "D戴佩妮", "v": "戴佩妮演唱会4K" }, { "n": "F飞儿乐队", "v": "飞儿乐队演唱会4K" }, { "n": "F费玉清", "v": "费玉清演唱会4K" }, { "n": "F费翔", "v": "费翔演唱会4K" }, { "n": "F方大同", "v": "方大同演唱会4K" }, { "n": "F房东的猫", "v": "房东的猫演唱会4K" }, { "n": "F凤飞飞", "v": "凤飞飞演唱会4K" }, { "n": "F凤凰传奇", "v": "凤凰传奇演唱会4K" }, { "n": "G郭采洁", "v": "郭采洁MV4K" }, { "n": "G光良", "v": "光良演唱会4K" }, { "n": "G郭静", "v": "郭静演唱会4K" }, { "n": "G郭富城", "v": "郭富城演唱会4K" }, { "n": "H胡彦斌", "v": "胡彦斌演唱会4K" }, { "n": "H胡夏", "v": "胡夏演唱会4K" }, { "n": "H韩红", "v": "韩红演唱会4K" }, { "n": "H黄品源", "v": "黄品源演唱会4K" }, { "n": "H黄小琥", "v": "黄小琥演唱会4K" }, { "n": "H花儿乐队", "v": "花儿乐队演唱会4K" }, { "n": "H黄家强", "v": "黄家强演唱会4K" }, { "n": "H后街男孩", "v": "后街男孩演唱会4K" }, { "n": "J经典老歌", "v": "经典老歌4K" }, { "n": "J贾斯丁比伯", "v": "贾斯丁比伯演唱会4K" }, { "n": "J金池", "v": "金池演唱会4K" }, { "n": "J金志文", "v": "金志文演唱会4K" }, { "n": "J焦迈奇", "v": "焦迈奇演唱会4K" }, { "n": "K筷子兄弟", "v": "筷子兄弟演唱会4K" }, { "n": "L李玟", "v": "李玟演唱会4K" }, { "n": "L林忆莲", "v": "林忆莲演唱会4K" }, { "n": "L李克勤", "v": "李克勤演唱会4K" }, { "n": "L刘宪华", "v": "刘宪华演唱会4K" }, { "n": "L李圣杰", "v": "李圣杰演唱会4K" }, { "n": "L林宥嘉", "v": "林宥嘉演唱会4K" }, { "n": "L梁静茹", "v": "梁静茹演唱会4K" }, { "n": "L李健", "v": "李健演唱会4K" }, { "n": "L林俊杰", "v": "林俊杰演唱会4K" }, { "n": "L李玉刚", "v": "李玉刚演唱会4K" }, { "n": "L林志炫", "v": "林志炫演唱会4K" }, { "n": "L李荣浩", "v": "李荣浩演唱会4K" }, { "n": "L李宇春", "v": "李宇春演唱会4K" }, { "n": "L洛天依", "v": "洛天依演唱会4K" }, { "n": "L林子祥", "v": "林子祥演唱会4K" }, { "n": "L李宗盛", "v": "李宗盛演唱会4K" }, { "n": "L黎明", "v": "黎明演唱会4K" }, { "n": "L刘德华", "v": "刘德华演唱会4K" }, { "n": "L罗大佑", "v": "罗大佑演唱会4K" }, { "n": "L林肯公园", "v": "林肯公园演唱会4K" }, { "n": "LLadyGaga", "v": "LadyGaga演唱会4K" }, { "n": "L旅行团乐队", "v": "旅行团乐队演唱会4K" }, { "n": "M莫文蔚", "v": "莫文蔚演唱会4K" }, { "n": "M毛不易", "v": "毛不易演唱会4K" }, { "n": "M梅艳芳", "v": "梅艳芳演唱会4K" }, { "n": "M迈克尔杰克逊", "v": "迈克尔杰克逊演唱会4K" }, { "n": "N南拳妈妈", "v": "南拳妈妈演唱会4K" }, { "n": "P朴树", "v": "朴树演唱会4K" }, { "n": "Q齐秦", "v": "齐秦演唱会4K" }, { "n": "Q青鸟飞鱼", "v": "青鸟飞鱼演唱会4K" }, { "n": "R容祖儿", "v": "容祖儿演唱会4K" }, { "n": "R热歌", "v": "热歌MV4K" }, { "n": "R任贤齐", "v": "任贤齐演唱会4K" }, { "n": "S水木年华", "v": "水木年华演唱会4K" }, { "n": "S孙燕姿", "v": "孙燕姿演唱会4K" }, { "n": "S苏打绿", "v": "苏打绿演唱会4K" }, { "n": "SSHE", "v": "SHE演唱会4K" }, { "n": "S孙楠", "v": "孙楠演唱会4K" }, { "n": "T陶喆", "v": "陶喆演唱会4K" }, { "n": "T谭咏麟", "v": "谭咏麟演唱会4K" }, { "n": "T田馥甄", "v": "田馥甄演唱会4K" }, { "n": "T谭维维", "v": "谭维维演唱会4K" }, { "n": "T逃跑计划", "v": "逃跑计划演唱会4K" }, { "n": "T田震", "v": "田震演唱会4K" }, { "n": "T谭晶", "v": "谭晶演唱会4K" }, { "n": "T屠洪刚", "v": "屠洪刚演唱会4K" }, { "n": "T泰勒·斯威夫特", "v": "泰勒·斯威夫特演唱会4K" }, { "n": "W王力宏", "v": "王力宏演唱会4K" }, { "n": "W王杰", "v": "王杰演唱会4K" }, { "n": "W吴克群", "v": "吴克群演唱会4K" }, { "n": "W王心凌", "v": "王心凌演唱会4K" }, { "n": "W汪峰", "v": "汪峰演唱会4K" }, { "n": "W伍佰", "v": "伍佰演唱会4K" }, { "n": "W王菲", "v": "王菲演唱会4K" }, { "n": "W五月天", "v": "五月天演唱会4K" }, { "n": "W汪苏泷", "v": "汪苏泷演唱会4K" }, { "n": "X徐佳莹", "v": "徐佳莹演唱会4K" }, { "n": "X弦子", "v": "弦子演唱会4K" }, { "n": "X萧亚轩", "v": "萧亚轩演唱会4K" }, { "n": "X许巍", "v": "许巍演唱会4K" }, { "n": "X薛之谦", "v": "薛之谦演唱会4K" }, { "n": "X许嵩", "v": "许嵩演唱会4K" }, { "n": "X小虎队", "v": "小虎队演唱会4K" }, { "n": "X萧敬腾", "v": "萧敬腾演唱会4K" }, { "n": "X谢霆锋", "v": "谢霆锋演唱会4K" }, { "n": "X徐小凤", "v": "徐小凤演唱会4K" }, { "n": "X信乐队", "v": "信乐队演唱会4K" }, { "n": "Y夜愿乐队", "v": "夜愿乐队演唱会4K" }, { "n": "Y原创音乐", "v": "原创音乐演唱会4K" }, { "n": "Y羽泉", "v": "羽泉演唱会4K" }, { "n": "Y粤语", "v": "粤语MV4K" }, { "n": "Y郁可唯", "v": "郁可唯演唱会4K" }, { "n": "Y叶倩文", "v": "叶倩文演唱会4K" }, { "n": "Y杨坤", "v": "杨坤演唱会4K" }, { "n": "Y庾澄庆", "v": "庾澄庆演唱会4K" }, { "n": "Y尤长靖", "v": "尤长靖演唱会4K" }, { "n": "Y易烊千玺", "v": "易烊千玺演唱会4K" }, { "n": "Y袁娅维", "v": "袁娅维演唱会4K" }, { "n": "Y杨丞琳", "v": "杨丞琳演唱会4K" }, { "n": "Y杨千嬅", "v": "杨千嬅演唱会4K" }, { "n": "Y杨宗纬", "v": "杨宗纬演唱会4K" }, { "n": "Z周杰伦", "v": "周杰伦演唱会4K" }, { "n": "Z张学友", "v": "张学友演唱会4K" }, { "n": "Z张信哲", "v": "张信哲演唱会4K" }, { "n": "Z张宇", "v": "张宇演唱会4K" }, { "n": "Z周华健", "v": "周华健演唱会4K" }, { "n": "Z张韶涵", "v": "张韶涵演唱会4K" }, { "n": "Z周深", "v": "周深演唱会4K" }, { "n": "Z纵贯线", "v": "纵贯线演唱会4K" }, { "n": "Z赵雷", "v": "赵雷演唱会4K" }, { "n": "Z周传雄", "v": "周传雄演唱会4K" }, { "n": "Z张国荣", "v": "张国荣演唱会4K" }, { "n": "Z周慧敏", "v": "周慧敏演唱会4K" }, { "n": "Z张惠妹", "v": "张惠妹演唱会4K" }, { "n": "Z周笔畅", "v": "周笔畅演唱会4K" }, { "n": "Z郑中基", "v": "郑中基演唱会4K" }, { "n": "Z张艺兴", "v": "张艺兴演唱会4K" }, { "n": "Z张震岳", "v": "张震岳演唱会4K" }, { "n": "Z张雨生", "v": "张雨生演唱会4K" }, { "n": "Z郑智化", "v": "郑智化演唱会4K" }, { "n": "Z卓依婷", "v": "卓依婷演唱会4K" }, { "n": "Z中岛美雪", "v": "中岛美雪演唱会4K" }] },
        { "key": "duration", "name": "时长", "value": [{ "n": "全部时长", "v": "0" }, { "n": "60分钟以上", "v": "4" }, { "n": "30~60分钟", "v": "3" }, { "n": "10~30分钟", "v": "2" }, { "n": "10分钟以下", "v": "1" }] }
    ]
};

// ==========================================
//          主逻辑
// ==========================================
const _home = async ({ filter }) => {
    return { class: CLASSES, list: [], filters: FILTERS };
};

const _homeVideo = async () => {
    const url = 'https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1';
    try {
        const { data } = await axios.get(url, { headers: BILI_HEADERS });
        let videos = [];
        if (data.data && data.data.list) {
            videos = data.data.list.map(item => ({
                vod_id: item.aid + "",
                vod_name: item.title.replace(/<[^>]*>/g, ""),
                vod_pic: fixCover(item.pic),
                vod_remarks: formatDuration(item.duration)
            }));
        }
        return { list: videos };
    } catch (e) { return { list: [] }; }
};

const _category = async ({ id, page, filter, filters }) => {
    page = Math.max(1, parseInt(page) || 1);
    const url = 'https://api.bilibili.com/x/web-interface/search/type';
    const params = { search_type: 'video', keyword: id, page: page };
    if (filters) {
        if (filters.order) params.order = filters.order;
        if (filters.duration) params.duration = filters.duration;
        if (filters.tid) params.keyword = filters.tid; 
    }
    try {
        const { data } = await axios.get(url, { params, headers: BILI_HEADERS });
        let videos = [];
        if (data.data && data.data.result) {
            videos = data.data.result.filter(item => item.type === 'video').map(item => ({
                vod_id: item.aid + "",
                vod_name: item.title.replace(/<[^>]*>/g, ""),
                vod_pic: fixCover(item.pic),
                vod_remarks: formatSearchDuration(item.duration)
            }));
        }
        return { list: videos, page: page, pagecount: data.data.numPages || 1, limit: 20, total: data.data.numResults || videos.length };
    } catch (e) { return { list: [] }; }
};

const _detail = async ({ id }) => {
    const result = { list: [] };
    const ids = Array.isArray(id) ? id : [id];
    for (const vid of ids) {
        try {
            const { data } = await axios.get('https://api.bilibili.com/x/web-interface/view?aid=' + vid, { headers: BILI_HEADERS });
            if (data.data) {
                const video = data.data;
                let playUrl = '';
                video.pages.forEach((page, index) => {
                    playUrl += `${page.part || `第${index + 1}集`}$${vid}_${page.cid}#`;
                });
                playUrl = playUrl.replace(/#$/g, '');
                result.list.push({
                    vod_id: vid,
                    vod_name: video.title.replace(/<[^>]*>/g, ""),
                    vod_pic: fixCover(video.pic),
                    vod_content: video.desc,
                    vod_play_from: "B站",
                    vod_play_url: playUrl
                });
            }
        } catch (e) { }
    }
    return result;
};

// ==========================================
//          核心播放逻辑 (多线路)
// ==========================================
const _play = async ({ flag, flags, id, req }) => {
    try {
        const parts = id.split('_');
        const avid = parts[0];
        const cid = parts[1];
        const loggedIn = isLoggedIn();
        
        // 1. 获取 B站数据
        const getDash = async () => {
             return axios.get('https://api.bilibili.com/x/player/playurl', {
                params: { avid, cid, qn: 120, fnval: 4048, fnver: 0, fourk: 1, ...(!loggedIn ? { try_look: 1 } : {}) },
                headers: BILI_HEADERS
            }).catch(()=>({data:{}}));
        };
        const getFlv = async () => {
             return axios.get('https://api.bilibili.com/x/player/playurl', {
                params: { avid, cid, qn: 112, fnval: 1, fnver: 0, fourk: 1, ...(!loggedIn ? { try_look: 1 } : {}) },
                headers: BILI_HEADERS
            }).catch(()=>({data:{}}));
        };
        
        const [dashRes, flvRes] = await Promise.all([getDash(), getFlv()]);
        
        const availableQualities = [];
        const qualityNameMap = { 127: '8K', 126: '杜比', 125: 'HDR', 120: '4K', 116: '1080P60', 112: '1080P+', 80: '1080P', 64: '720P', 32: '480P' };
        
        // 2. [猫爪] 直连模式 (排序第一)
        if (dashRes.data.code === 0 && dashRes.data.data?.dash) {
            const d = dashRes.data.data.dash;
            
            // 【关键修改】不再过滤编码，直接取 ID 最高的 (4K/8K)
            const bestVideo = d.video?.sort((a,b)=>b.id-a.id)[0];
            const bestAudio = d.audio?.[0]; 
            
            if (bestVideo && bestAudio) {
                // CatTV 直连
                availableQualities.push({
                    name: `[猫爪] 直连线路`,
                    url: bestVideo.baseUrl || bestVideo.base_url,
                    audio: bestAudio.baseUrl || bestAudio.base_url,
                    priority: 110
                });

                // TVBox 代理 (【修复3002参数】)
                const info = getRequestInfo(req);
                const isEscape = !info.userAgent.toLowerCase().includes("okhttp");
                
                // 完全对齐图1的参数结构
                const proxyUrl = `${info.fullUrl}${meta.api}/proxy?ac=proxy&ids=${avid}_${cid}&type=mpd&qn=120&isEscape=${isEscape}`;
                
                availableQualities.push({
                    name: `[影视] 代理线路`,
                    url: proxyUrl,
                    priority: 100 
                });
            }
        }
        
        // 3. [兼容] 通用模式
        if (flvRes.data.code === 0 && flvRes.data.data?.durl?.[0]) {
             const qn = flvRes.data.data.quality;
             availableQualities.push({
                name: `[兼容] ${qualityNameMap[qn]||qn}P`,
                url: flvRes.data.data.durl[0].url,
                priority: 90
            });
        }
        
        availableQualities.sort((a, b) => b.priority - a.priority);
        const urlArray = [];
        availableQualities.forEach(q => { urlArray.push(q.name); urlArray.push(q.url); });
        
        const directItem = availableQualities.find(q => q.name.includes('猫爪'));
        
        return {
            parse: 0,
            url: urlArray,
            header: { "User-Agent": BILI_HEADERS["User-Agent"], "Referer": "https://www.bilibili.com" },
            extra: { audio: directItem ? directItem.audio : "" }
        };

    } catch (e) {
        return { parse: 0, url: "", header: {} };
    }
};

// ==========================================
//          Proxy 接口 (接收新参数)
// ==========================================
const _proxy = async (req, reply) => {
    const { ids } = req.query; // ids 还是需要的
    
    if (!ids) {
        if (reply.code) reply.code(404);
        return "";
    }

    if (reply.header) {
        reply.header('Access-Control-Allow-Origin', '*');
        reply.header('Content-Type', 'application/dash+xml');
    }
    
    const [avid, cid] = ids.split("_");
    try {
        const { data } = await axios.get('https://api.bilibili.com/x/player/playurl', {
             params: { avid, cid, qn: 120, fnval: 4048, fnver: 0, fourk: 1, try_look: 1 },
             headers: BILI_HEADERS
        });
        
        if (data.code === 0 && data.data?.dash) {
            // 将 req.query 传入 getMpd，以便读取 isEscape
            const xml = getMpd(data.data.dash, req.query);
            if (reply.send) return reply.send(xml);
            return xml;
        } else {
             if (reply.code) reply.code(404);
             return "";
        }
    } catch (e) {
        if (reply.code) reply.code(500);
        return "";
    }
};

const meta = { key: "bilibili_all", name: "哔哩大全", type: 4, api: "/video/bilibili_all", searchable: 1, quickSearch: 1, changeable: 0 };
const store = { init: false };
const init = async (server) => { if (store.init) return; store.log = server.log; store.init = true; };

module.exports = async (app, opt) => {
    app.get(meta.api, async (req, reply) => {
        if (!store.init) await init(req.server);
        const { ac, ids, play, wd, pg, filter, t, ext } = req.query;
        if (play) return await _play({ id: play, req });
        if (wd) return await _search({ page: pg || 1, wd });
        if (!ac) return await _home({ filter });
        if (ac === "detail") {
            if (t) return await _category({ id: t, page: pg || 1, filters: ext ? JSON.parse(Buffer.from(ext, 'base64').toString()) : {} });
            if (ids) return await _detail({ id: ids.split(",") });
            return await _homeVideo();
        }
        return req.query;
    });
    app.get(`${meta.api}/proxy`, { attachValidation: true }, _proxy);
    opt.sites.push(meta);
};