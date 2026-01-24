const crypto = require("crypto");
const axios = require("axios");
const cheerio = require("cheerio");
const https = require("https");

// ========== 全局配置 ==========
const host = 'https://www.dyg123.net';

// 缓存系统
class CacheManager {
    constructor(ttl = 300000) {
        this.cache = new Map();
        this.ttl = ttl;
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;
        
        if (Date.now() - item.timestamp > this.ttl) {
            this.cache.delete(key);
            return null;
        }
        
        return item.data;
    }

    set(key, data) {
        this.cache.set(key, { data, timestamp: Date.now() });
    }

    clear() {
        this.cache.clear();
    }
}

// 全局缓存实例
const cache = new CacheManager();

// 优化axios实例配置
const axiosInstance = axios.create({
    httpsAgent: new https.Agent({ 
        rejectUnauthorized: false,
        keepAlive: true,
        maxSockets: 5
    }),
    timeout: 10000,
    maxRedirects: 5,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
});

// ========== 工具函数 ==========
const utils = {
    // 字符串截取函数（模仿原规则中的cutStr）
    cutStr: function(str, prefix = '', suffix = '', defaultVal = 'cutFaile', clean = true, i = 1, all = false) {
        try {
            if (!str || typeof str !== 'string') {
                return all ? [defaultVal] : defaultVal;
            }
            
            const cleanStr = cs => String(cs).replace(/<[^>]*?>/g, ' ')
                .replace(/(&nbsp;|\u00A0|\s)+/g, ' ')
                .trim()
                .replace(/\s+/g, ' ');
            
            const esc = s => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            let pre = esc(prefix).replace(/£/g, '[^]*?');
            let end = esc(suffix);
            let regex = new RegExp(`${pre ? pre : '^'}([^]*?)${end ? end : '$'}`, 'g');
            let matchArr = [...str.matchAll(regex)];
            
            if (matchArr.length === 0) {
                return all ? [defaultVal] : defaultVal;
            }
            
            if (all) {
                return matchArr.map(it => {
                    const val = it[1] ?? defaultVal;
                    return clean && val !== defaultVal ? cleanStr(val) : val;
                });
            }
            
            i = parseInt(i, 10);
            if (isNaN(i) || i < 1) {
                i = 0;
            }
            i = i - 1;
            if (i >= matchArr.length) {
                return defaultVal;
            }
            
            let result = matchArr[i][1] ?? defaultVal;
            return clean && result !== defaultVal ? cleanStr(result) : result;
        } catch (e) {
            console.error(`字符串截取失败：`, e.message);
            return all ? ['cutErr'] : 'cutErr';
        }
    },

    // 获取视频列表（模仿原规则中的getVodList）
    getVodList: function(html) {
        try {
            if (!html) {
                return [];
            }
            
            const $ = cheerio.load(html);
            const kvods = [];
            
            $('.m1').each((index, element) => {
                const $el = $(element);
                const link = $el.find('a');
                
                if (link.length === 0) return;
                
                const href = link.attr('href');
                const kname = link.find('img').attr('alt') || '未知名称';
                const kpic = link.find('img').attr('data-original') || link.find('img').attr('src') || '';
                const kremarks = $el.find('.other').text().trim() || '状态未知';
                
                kvods.push({
                    vod_name: kname,
                    vod_pic: kpic.startsWith('http') ? kpic : new URL(kpic, host).href,
                    vod_remarks: kremarks,
                    vod_id: `${href}@${kname}@${kpic}@${kremarks}`
                });
            });
            
            return kvods;
        } catch (e) {
            console.error(`生成视频列表失败：`, e.message);
            return [];
        }
    },

    // 获取播放列表 - 屏蔽下载线路，只保留在线播放线路
    parsePlayUrls: function(html) {
        const $ = cheerio.load(html);
        const playFrom = [];
        const playUrl = [];
        
        // 只解析在线播放线路，跳过磁力下载线路
        // 解析在线播放线路的标题
        $('#tab81').each((index, element) => {
            const text = $(element).text().trim();
            if (text) {
                playFrom.push(text || `在线线路${index + 1}`);
            }
        });
        
        // 如果没找到在线线路标题，使用默认标题
        if (playFrom.length === 0) {
            playFrom.push('在线播放');
        }
        
        // 只解析在线播放链接，跳过磁力链接
        $('.videourl').each((index, element) => {
            const links = [];
            $(element).find('a').each((i, a) => {
                const text = $(a).text().trim();
                const href = $(a).attr('href');
                if (text && href) {
                    // 跳过磁力链接
                    if (href.startsWith('magnet:') || href.includes('magnet') || 
                        text.includes('磁力') || text.includes('下载') || 
                        text.includes('BT') || text.includes('种子')) {
                        return; // 跳过这个链接
                    }
                    
                    const fullUrl = href.startsWith('http') ? href : new URL(href, host).href;
                    links.push(`${text}$${fullUrl}`);
                }
            });
            if (links.length > 0) {
                playUrl.push(links.join('#'));
            }
        });
        
        // 如果没有找到在线播放链接，尝试查找其他可能的在线播放链接
        if (playUrl.length === 0) {
            // 查找iframe或其他播放器链接
            $('iframe').each((index, element) => {
                const src = $(element).attr('src');
                if (src && (src.includes('m3u8') || src.includes('mp4') || 
                           src.includes('player') || src.includes('play'))) {
                    const fullUrl = src.startsWith('http') ? src : new URL(src, host).href;
                    playUrl.push(`在线播放$${fullUrl}`);
                }
            });
            
            // 查找script中的播放链接
            const scripts = $('script').text();
            const m3u8Match = scripts.match(/["'](http[^"']*\.m3u8[^"']*)["']/);
            const mp4Match = scripts.match(/["'](http[^"']*\.mp4[^"']*)["']/);
            
            if (m3u8Match) {
                playUrl.push(`在线播放$${m3u8Match[1]}`);
            } else if (mp4Match) {
                playUrl.push(`在线播放$${mp4Match[1]}`);
            }
        }
        
        // 如果没有找到任何播放线路，添加默认空线路
        if (playFrom.length === 0) {
            playFrom.push('在线播放');
        }
        if (playUrl.length === 0) {
            playUrl.push('');
        }
        
        return {
            playFrom: playFrom.join('$$$'),
            playUrl: playUrl.join('$$$')
        };
    },

    // 获取详情信息
    parseDetail: function(html, id, kname, kpic, kremarks) {
        try {
            const $ = cheerio.load(html);
            const detailText = $('.ct-l').text();
            
            // 使用原规则中的cutStr逻辑提取信息
            const cut = (prefix, suffix, def) => this.cutStr(detailText, prefix, suffix, def);
            
            const type_name = cut('◎类别', '◎', '类型');
            const vod_remarks = cut('◎集数', '◎', kremarks || '状态');
            const vod_year = cut('◎年代', '◎', '');
            const vod_area = cut('◎产地', '◎', '');
            const vod_lang = cut('◎语言', '◎', '');
            const vod_director = cut('◎导演', '◎', '');
            
            let vod_actor = cut('◎演员', '</p>', '') || cut('◎主演', '</p>', '');
            if (!vod_actor || vod_actor === 'cutFaile') {
                vod_actor = cut('◎演员', '◎', '') || cut('◎主演', '◎', '');
            }
            
            let vod_content = cut('◎简介£>', '</p>', '') || kname;
            if (!vod_content || vod_content === 'cutFaile') {
                vod_content = cut('◎简介', '</p>', '') || kname;
            }
            
            // 解析播放列表 - 只获取在线播放线路
            const { playFrom, playUrl } = this.parsePlayUrls(html);
            
            // 如果没有有效的播放链接，尝试从其他位置获取
            let finalPlayUrl = playUrl;
            if (!playUrl || playUrl === '' || playUrl === 'cutErr') {
                // 尝试从其他位置查找播放链接
                const videoSrc = $('video source').attr('src');
                if (videoSrc) {
                    finalPlayUrl = `在线播放$${videoSrc}`;
                }
            }
            
            return {
                vod_id: id,
                vod_name: kname,
                vod_pic: kpic.startsWith('http') ? kpic : new URL(kpic, host).href,
                type_name: type_name,
                vod_remarks: vod_remarks,
                vod_year: vod_year,
                vod_area: vod_area,
                vod_lang: vod_lang,
                vod_director: vod_director,
                vod_actor: vod_actor,
                vod_content: vod_content.replace(/[\u3000\s]+/g, ' ').trim(),
                vod_play_from: playFrom,
                vod_play_url: finalPlayUrl
            };
        } catch (e) {
            console.error(`解析详情失败：`, e.message);
            return null;
        }
    },

    // 获取真实播放地址 - 屏蔽磁力链接
    parsePlayUrl: async function(url) {
        try {
            // 屏蔽磁力链接
            if (url.startsWith('magnet:')) {
                return { jx: 0, parse: 0, url: '' };
            }
            
            // 屏蔽包含磁力关键词的链接
            if (url.includes('magnet') || url.includes('bt') || 
                url.includes('torrent') || url.includes('种子')) {
                return { jx: 0, parse: 0, url: '' };
            }
            
            const response = await axiosInstance.get(url);
            const html = response.data;
            
            // 尝试第一种格式
            let jurl = this.cutStr(html, "a:'", "'", '');
            if (jurl && /m3u8|mp4|mkv/.test(jurl)) {
                return { jx: 0, parse: 0, url: jurl };
            }
            
            // 尝试第二种格式
            jurl = this.cutStr(html, '<iframe£src="', '"', '');
            if (jurl) {
                const iframeResponse = await axiosInstance.get(jurl);
                const iframeHtml = iframeResponse.data;
                const kurl = new URL(jurl).origin + this.cutStr(iframeHtml, 'url = "', '"', '');
                
                if (kurl && /m3u8|mp4|mkv/.test(kurl)) {
                    return { jx: 0, parse: 0, url: kurl };
                }
                return { jx: 0, parse: 1, url: kurl || url };
            }
            
            return { jx: 0, parse: 1, url: url };
        } catch (e) {
            console.error(`解析播放地址失败：`, e.message);
            return { jx: 0, parse: 1, url: url };
        }
    }
};

// ========== API请求工具 ==========
const apiUtil = {
    // 获取首页推荐
    getHome: async (page = 1) => {
        const cacheKey = `home_${page}`;
        const cached = cache.get(cacheKey);
        if (cached) return cached;
        
        try {
            const response = await axiosInstance.get(`${host}/`);
            const list = utils.getVodList(response.data);
            
            const result = {
                list: list,
                page: page,
                pagecount: 1
            };
            
            cache.set(cacheKey, result);
            return result;
        } catch (e) {
            console.error(`获取首页失败：`, e.message);
            return { list: [], page: page, pagecount: 0 };
        }
    },

    // 获取分类列表
    getCategory: async (classid, page = 1, orderby = 'newstime') => {
        const cacheKey = `category_${classid}_${page}_${orderby}`;
        const cached = cache.get(cacheKey);
        if (cached) return cached;
        
        try {
            const url = `${host}/e/action/ListInfo.php?classid=${classid}&page=${page - 1}&line=30&tempid=1&orderby=${orderby}`;
            const response = await axiosInstance.get(url);
            const list = utils.getVodList(response.data);
            
            const result = {
                list: list,
                page: page,
                pagecount: Math.ceil(list.length / 30) + 1
            };
            
            cache.set(cacheKey, result);
            return result;
        } catch (e) {
            console.error(`获取分类失败：`, e.message);
            return { list: [], page: page, pagecount: 0 };
        }
    },

    // 搜索视频
    search: async (keyword, page = 1) => {
        const cacheKey = `search_${keyword}_${page}`;
        const cached = cache.get(cacheKey);
        if (cached) return cached;
        
        try {
            // 第一轮搜索
            const fbody = `keyboard=${encodeURIComponent(keyword)}&submit=搜索&show=title&tempid=1`;
            const response1 = await axiosInstance.post(
                `${host}/e/search/index.php`,
                fbody,
                {
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
                    }
                }
            );
            
            let list = utils.getVodList(response1.data);
            
            // 获取searchid进行第二轮搜索
            const flagNum = utils.cutStr(response1.data, 'searchid=', '"', '');
            if (flagNum) {
                const response2 = await axiosInstance.get(
                    `${host}/e/search/result/index.php?page=1&searchid=${flagNum}`
                );
                const moreList = utils.getVodList(response2.data);
                list = [...list, ...moreList];
            }
            
            // 去重
            const uniqueList = [];
            const seenIds = new Set();
            
            list.forEach(item => {
                if (!seenIds.has(item.vod_id)) {
                    seenIds.add(item.vod_id);
                    uniqueList.push(item);
                }
            });
            
            const result = {
                list: uniqueList,
                page: page,
                pagecount: 1
            };
            
            cache.set(cacheKey, result);
            return result;
        } catch (e) {
            console.error(`搜索失败：`, e.message);
            return { list: [], page: page, pagecount: 0 };
        }
    },

    // 获取详情 - 屏蔽下载线路
    getDetail: async (id) => {
        const cacheKey = `detail_${id}`;
        const cached = cache.get(cacheKey);
        if (cached) return cached;
        
        try {
            const [idPart, kname, kpic, kremarks] = id.split('@');
            const response = await axiosInstance.get(idPart.startsWith('http') ? idPart : `${host}${idPart}`);
            
            const detail = utils.parseDetail(response.data, idPart, kname, kpic, kremarks);
            
            if (!detail) {
                return { list: [] };
            }
            
            // 过滤掉空的播放链接
            if (detail.vod_play_url === '') {
                detail.vod_play_url = '无在线播放资源';
            }
            
            const result = { list: [detail] };
            cache.set(cacheKey, result);
            return result;
        } catch (e) {
            console.error(`获取详情失败：`, e.message);
            return { list: [] };
        }
    },

    // 获取播放地址 - 屏蔽磁力链接
    getPlayUrl: async (url) => {
        try {
            // 检查是否为磁力链接，如果是则返回空
            if (url.startsWith('magnet:') || url.includes('magnet')) {
                return { jx: 0, parse: 0, url: '' };
            }
            
            const playInfo = await utils.parsePlayUrl(url);
            return playInfo;
        } catch (e) {
            console.error(`获取播放地址失败：`, e.message);
            return { jx: 0, parse: 1, url: url };
        }
    }
};

// ========== 主要功能函数 ==========
const _home = async ({ filter, page = 1 }) => {
    // 返回分类信息
    return {
        class: [
            { type_id: '1', type_name: '电影' },
            { type_id: '20', type_name: '剧集' },
            { type_id: '31', type_name: '综艺' },
            { type_id: '30', type_name: '动画' },
            { type_id: '32', type_name: '短剧' }
        ]
    };
};

const _category = async ({ id, page = 1, filter, filters }) => {
    const orderby = filters?.orderby || 'newstime';
    return await apiUtil.getCategory(id, page, orderby);
};

const _detail = async ({ ids }) => {
    if (!ids) {
        return { list: [] };
    }
    
    const idList = Array.isArray(ids) ? ids : [ids];
    const result = await apiUtil.getDetail(idList[0]);
    return result;
};

const _play = async ({ id, flags }) => {
    if (!id) {
        return { parse: 0, url: '' };
    }
    
    // id格式可能是: 播放地址 或者 详情ID
    if (id.includes('@')) {
        // 这是详情ID，需要先获取详情再解析播放地址
        const detailResult = await apiUtil.getDetail(id);
        if (detailResult.list.length > 0 && detailResult.list[0].vod_play_url) {
            const playUrls = detailResult.list[0].vod_play_url.split('$$$');
            const playFroms = detailResult.list[0].vod_play_from.split('$$$');
            
            // 遍历所有线路，找到第一个有效的在线播放链接
            for (let i = 0; i < playUrls.length; i++) {
                if (playUrls[i]) {
                    const episodeList = playUrls[i].split('#');
                    for (let j = 0; j < episodeList.length; j++) {
                        if (episodeList[j]) {
                            const parts = episodeList[j].split('$$');
                            if (parts.length > 1) {
                                const playUrl = parts[1];
                                // 检查是否为磁力链接，如果是则跳过
                                if (!playUrl.startsWith('magnet:') && !playUrl.includes('magnet')) {
                                    const result = await apiUtil.getPlayUrl(playUrl);
                                    if (result.url) {
                                        return result;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        return { parse: 0, url: '' };
    } else {
        // 直接是播放地址，检查是否为磁力链接
        if (id.startsWith('magnet:') || id.includes('magnet')) {
            return { parse: 0, url: '' };
        }
        // 直接是播放地址
        return await apiUtil.getPlayUrl(id);
    }
};

const _search = async ({ wd, page = 1 }) => {
    if (!wd) {
        return { list: [], page: page, pagecount: 0 };
    }
    
    return await apiUtil.search(wd, page);
};

// ========== 站点元数据 ==========
const meta = {
    key: "DianYingGang",
    name: "电影港",
    type: 4,
    api: "/video/DianYingGang"
};

const store = { init: false };
const init = async (server) => {
    if (store.init) return;
    store.log = server.log;
    global.store = store;
    store.init = true;
    
    store.log.info(`电影港(纯净版)初始化完成，已屏蔽下载线路`);
};

// ========== 模块导出 ==========
module.exports = async (app, opt) => {
    app.get(meta.api, async (req, reply) => {
        if (!store.init) await init(req.server);
        const { extend, filter, t, ac, pg, ext, ids, play, wd, quick } = req.query;

        try {
            if (play) {
                return await _play({ id: play, flags: ext });
            } else if (wd) {
                return await _search({ wd: wd, page: parseInt(pg || "1") });
            } else if (!ac) {
                return await _home({ filter: filter ?? false, page: parseInt(pg || "1") });
            } else if (ac === "detail") {
                if (t) {
                    const filters = filter ? JSON.parse(filter) : {};
                    return await _category({ 
                        id: t, 
                        page: parseInt(pg || "1"), 
                        filters: filters 
                    });
                } else if (ids) {
                    return await _detail({ ids: ids });
                }
            }
            return { code: 404, msg: "未知请求" };
        } catch (e) {
            if (global.store) store.log.error(`请求处理失败: ${e.message}`);
            return { code: 500, msg: "服务器内部错误" };
        }
    });
    
    // 添加清除缓存路由
    app.get(`${meta.api}/clear-cache`, async (req, reply) => {
        cache.clear();
        if (global.store) store.log.info("缓存已清空");
        return { code: 200, msg: "缓存已清空" };
    });
    
    opt.sites.push(meta);
};