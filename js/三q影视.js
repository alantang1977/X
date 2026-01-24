const axios = require("axios");
const http = require("http");
const https = require("https");
const vm = require("node:vm");

const _http = axios.create({
    timeout: 15 * 1000,
    httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false }),
    httpAgent: new http.Agent({ keepAlive: true }),
});

const config = {
    host: 'https://qqqys.com',
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://qqqys.com'
    }
};

// --- 动态生成符合参考源码逻辑的年份 ---
const generateYears = (typeName) => {
    const currentYear = new Date().getFullYear();
    const years = [{ "n": "全部", "v": "" }];
    if (typeName === '电影') {
        for (let y = currentYear; y >= 2016; y--) years.push({ "n": String(y), "v": String(y) });
        ['2015-2011', '2010-2000', '90年代', '80年代', '更早'].forEach(i => years.push({ "n": i, "v": i }));
    } else if (typeName === '剧集') {
        for (let y = currentYear; y >= 2021; y--) years.push({ "n": String(y), "v": String(y) });
        ['2020-2016', '2015-2011', '2010-2000', '更早'].forEach(i => years.push({ "n": i, "v": i }));
    } else {
        for (let y = currentYear; y >= 2011; y--) years.push({ "n": String(y), "v": String(y) });
        years.push({ "n": "更早", "v": "更早" });
    }
    return years;
};

// --- 根据参考源码配置筛选器 ---
const filterData = {
    "电影": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["动作","喜剧","爱情","科幻","恐怖","悬疑","犯罪","战争","动画","冒险","历史","灾难","纪录","剧情"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","香港","台湾","美国","日本","韩国","泰国","印度","英国","法国","德国","加拿大","西班牙","意大利","澳大利亚"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('电影') }
    ],
    "剧集": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["爱情","古装","武侠","历史","家庭","喜剧","悬疑","犯罪","战争","奇幻","科幻","恐怖"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","香港","台湾","美国","日本","韩国","泰国","英国"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('剧集') }
    ],
    "动漫": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["冒险","奇幻","科幻","武侠","悬疑"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","日本","欧美"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('动漫') }
    ],
    "综艺": [
        { "key": "class", "name": "类型", "value": [{ "n": "全部", "v": "" }, ...["真人秀","音乐","脱口秀","歌舞","爱情"].map(i => ({ "n": i, "v": i }))] },
        { "key": "area", "name": "地区", "value": [{ "n": "全部", "v": "" }, ...["大陆","香港","台湾","美国","日本","韩国"].map(i => ({ "n": i, "v": i }))] },
        { "key": "year", "name": "年份", "value": generateYears('综艺') }
    ]
};

const QUALITY_PRIORITY = [
    { keywords: ['8K', '8k'], score: 200 },
    { keywords: ['4K', '4k', '超清4K'], score: 190 },
    { keywords: ['蓝光4K', '蓝光HDR'], score: 180 },
    { keywords: ['AE', '蓝光'], score: 170 },
    { keywords: ['1080P蓝光', '1080PHDR'], score: 160 },
    { keywords: ['1080P', '1080p', '超清'], score: 150 },
    { keywords: ['720P', '720p', '高清'], score: 140 },
    { keywords: ['480P', '480p', '标清'], score: 130 },
    { keywords: ['360P', '360p', '流畅'], score: 120 }
];

const json2vods = (arr) => (arr || []).map(i => ({
    vod_id: i.vod_id.toString(),
    vod_name: i.vod_name,
    vod_pic: i.vod_pic,
    vod_remarks: i.vod_remarks,
    type_name: i.vod_class ? `${i.type_name},${i.vod_class}` : i.type_name,
    vod_year: i.vod_year
}));

const calculateQualityScore = (showCode, lineName) => {
    const fullText = `${showCode}${lineName}`.toLowerCase();
    for (const rule of QUALITY_PRIORITY) {
        if (rule.keywords.some(k => fullText.includes(k.toLowerCase()))) return rule.score;
    }
    return 50;
};

const runJsChallenge = (code) => {
    try {
        return new vm.Script(code).runInContext(vm.createContext({}), { timeout: 1000 });
    } catch (e) { return ''; }
};

const getClasses = async () => {
    try {
        const res = await _http.get(`${config.host}/api.php/index/home`, { headers: config.headers });
        return {
            class: res.data.data.categories.map(i => ({ type_id: i.type_name, type_name: i.type_name })),
            filters: filterData
        };
    } catch (e) { return { class: [] }; }
};

const getCategoryList = async (tid, pg = 1, extend = {}) => {
    try {
        // 重要：修正 API 参数名，确保点击后能获取到数据
        let url = `${config.host}/api.php/filter/vod?type_name=${encodeURIComponent(tid)}&page=${pg}`;
        
        // 映射参数：网站后台通常接收 class, area, year
        if (extend.class) url += `&class=${encodeURIComponent(extend.class)}`;
        if (extend.area) url += `&area=${encodeURIComponent(extend.area)}`;
        if (extend.year) url += `&year=${encodeURIComponent(extend.year)}`;
        
        url += `&sort=hits`; // 默认按人气排序

        const res = await _http.get(url, { headers: config.headers });
        return {
            list: json2vods(res.data.data),
            page: pg,
            pagecount: res.data.pageCount
        };
    } catch (e) { return { list: [] }; }
};

const getDetail = async (id) => {
    try {
        const res = await _http.get(`${config.host}/api.php/vod/get_detail?vod_id=${id}`, { headers: config.headers });
        const data = res.data.data[0];
        const vodplayer = res.data.vodplayer;
        const rawShows = data.vod_play_from.split('$$$');
        const rawUrlsList = data.vod_play_url.split('$$$');
        const validLines = [];

        rawShows.forEach((showCode, index) => {
            const playerInfo = vodplayer.find(p => p.from === showCode);
            if (!playerInfo) return;
            let lineName = playerInfo.show;
            if (showCode.toLowerCase() !== lineName.toLowerCase()) lineName = `${lineName} (${showCode})`;
            const urls = rawUrlsList[index].split('#').map(urlItem => {
                if (urlItem.includes('$')) {
                    const [episode, url] = urlItem.split('$');
                    return `${episode}$${showCode}@${playerInfo.decode_status}@${url}`;
                }
                return null;
            }).filter(Boolean);
            if (urls.length > 0) {
                validLines.push({
                    lineName,
                    playUrls: urls.join('#'),
                    score: calculateQualityScore(showCode, lineName)
                });
            }
        });

        if (validLines.length === 0) return null;
        validLines.sort((a, b) => b.score - a.score);
        return {
            vod_id: data.vod_id,
            vod_name: data.vod_name,
            vod_pic: data.vod_pic,
            vod_remarks: data.vod_remarks,
            vod_content: data.vod_content,
            vod_play_from: validLines[0].lineName,
            vod_play_url: validLines[0].playUrls
        };
    } catch (e) { return null; }
};

const getPlayUrl = async (input) => {
    try {
        const [play_from, need_parse, raw_url] = input.split('@');
        let finalUrl = '';
        if (need_parse === '1') {
            let authToken = '';
            for (let i = 0; i < 2; i++) {
                const api = `${config.host}/api.php/decode/url/?url=${encodeURIComponent(raw_url)}&vodFrom=${play_from}${authToken}`;
                const res = await _http.get(api, { headers: config.headers });
                if (res.data.code === 2 && res.data.challenge) {
                    authToken = `&token=${runJsChallenge(res.data.challenge)}`;
                    continue;
                }
                if (res.data.data?.startsWith('http')) {
                    finalUrl = res.data.data;
                    break;
                }
            }
        }
        finalUrl = finalUrl || raw_url;
        return {
            parse: /(iqiyi|qq|youku|mgtv|bilibili)/.test(finalUrl) ? 1 : 0,
            url: finalUrl,
            header: { 'User-Agent': config.headers['User-Agent'] }
        };
    } catch (e) { return { parse: 0, url: input.split('@')[2] || input }; }
};

const search = async (wd, pg = 1) => {
    try {
        const res = await _http.get(`${config.host}/api.php/search/index?wd=${encodeURIComponent(wd)}&page=${pg}`, { headers: config.headers });
        return { list: json2vods(res.data.data), page: pg, pagecount: res.data.pageCount };
    } catch (e) { return { list: [] }; }
};

const handleT4Request = async (req) => {
    const { ac, t, ids, play, pg, wd, ext } = req.query;
    if (play) return await getPlayUrl(play);
    if (ids) {
        const detail = await getDetail(ids);
        return { list: detail ? [detail] : [] };
    }
    if (wd) return await search(wd, pg || 1);
    if (t) {
        let extend = {};
        if (ext) {
            try { extend = JSON.parse(Buffer.from(ext, 'base64').toString()); } catch (e) {}
        }
        return await getCategoryList(t, pg || 1, extend);
    }
    return await getClasses();
};

const meta = {
    key: "3qys_t4_fix",
    name: "3Q影视",
    type: 4,
    api: "/video/3qys",
    searchable: 1,
    quickSearch: 1
};

module.exports = async (app, opt) => {
    app.get(meta.api, async (req) => {
        try { return await handleT4Request(req); }
        catch (e) { return { error: e.message }; }
    });
    opt.sites.push(meta);
};
