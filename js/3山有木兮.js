 /** 
 * ============================================================================
 * 山有木兮 不夜版 (带筛选)
 * ============================================================================
 * 
 * 类型: 视频源 (Type 4)
 * 接口: /video/ShanYouMuXi
 * 站点: https://film.symx.club
 * 
 * [功能特性]
 * - 首页分类与筛选
 * - 视频搜索 (支持快速搜索)
 * - 分类列表 (支持地区/年份/语言/排序筛选)
 * - 视频详情 (多线路解析)
 * - 智能播放 (接口优先，失败自动嗅探)
 * 
 * [播放逻辑]
 * 1. 优先调用 /api/line/play/parse 获取真实播放地址 (parse: 0)
 * 2. 接口失败/超时/返回空时，自动回退到播放器页面嗅探 (parse: 1)
 * 
 * [更新时间]
 * 2025-02-07
**/
const axios = require("axios");
const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");

// 初始化日志系统 - 兼容 Fastify 的 log 对象，同时支持独立运行
let appLog = null;

const initLogger = (fastifyLog = null) => {
    if (fastifyLog) {
        appLog = fastifyLog;
    } else {
        // 独立运行时的简单日志
        appLog = {
            info: (msg) => console.log(`[INFO] ${msg}`),
            error: (msg) => console.error(`[ERROR] ${msg}`),
            warn: (msg) => console.warn(`[WARN] ${msg}`),
            debug: () => {} // 空实现
        };
    }
    return appLog;
};

// 获取日志实例（确保已初始化）
const getLogger = () => {
    if (!appLog) {
        return initLogger();
    }
    return appLog;
};

// 创建HTTP客户端实例
const _http = axios.create({
    timeout: 15 * 1000,
    httpsAgent: new https.Agent({ keepAlive: true, rejectUnauthorized: false }),
    httpAgent: new http.Agent({ keepAlive: true }),
});

// 山有木兮配置
const shanYouMuXiConfig = {
    host: "https://film.symx.club",
    headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Platform": "web",
        "Referer": "https://film.symx.club/"
    }
};

// 核心请求函数
const fetch = async (url, referer = '/') => {
    const log = getLogger();
    try {
        const response = await _http.get(url, {
            headers: {
                ...shanYouMuXiConfig.headers,
                "Referer": shanYouMuXiConfig.host + referer
            }
        });
        return response.data;
    } catch (error) {
        log.error(`HTTP请求失败: ${url}, ${error.message}`);
        return null;
    }
};

// 1. 播放解析 - 优先接口，失败则嗅探
const getPlayUrl = async (lineId) => {
    const parts = lineId.split(':');
    const filmId = parts[0] || '';
    const lineIdValue = parts[1] || lineId;
    const cid = parts[2] || '1';

    // 第一步：尝试直接获取播放地址
    try {
        const url = `${shanYouMuXiConfig.host}/api/line/play/parse?lineId=${encodeURIComponent(lineIdValue)}`;
        const response = await _http.get(url, {
            headers: {
                ...shanYouMuXiConfig.headers,
                "Referer": shanYouMuXiConfig.host + "/"
            },
            timeout: 10000
        });

        let data = response.data;
        if (typeof data === 'string') {
            try { data = JSON.parse(data); } catch (e) {}
        }

        // 如果获取到有效地址，直接返回
        if (data?.data && typeof data.data === 'string' && data.data.length > 0) {
            return {
                parse: 0,
                url: data.data,
                header: {
                    "User-Agent": shanYouMuXiConfig.headers["User-Agent"],
                    "Referer": shanYouMuXiConfig.host + "/"
                }
            };
        }
    } catch (error) {
        // 接口请求失败，继续回退到嗅探
    }

    // 第二步：接口失败，返回嗅探地址
    return {
        parse: 1,
        url: `${shanYouMuXiConfig.host}/player?cid=${cid}&film_id=${filmId}&line_id=${lineIdValue}`,
        header: {
            "User-Agent": shanYouMuXiConfig.headers["User-Agent"],
            "Referer": shanYouMuXiConfig.host + "/"
        }
    };
};


// 2. 获取视频详情
const getDetail = async (id) => {
    const data = await fetch(`${shanYouMuXiConfig.host}/api/film/detail?id=${encodeURIComponent(id)}`, '/');
    if (!data || !data.data) return { list: [] };

    const filmData = data.data;
    const shows = [];
    const play_urls = [];

    if (filmData.playLineList && Array.isArray(filmData.playLineList)) {
        filmData.playLineList.forEach(line => {
            shows.push(line.playerName);
            play_urls.push(line.lines.map(ep => `${ep.name}$${filmData.id}:${ep.id}:1`).join('#'));
        });
    }

    return {
        list: [{
            vod_id: id,
            vod_name: filmData.name || '',
            vod_pic: filmData.cover || '',
            vod_year: filmData.year || '',
            vod_area: filmData.other || '',
            vod_actor: filmData.actor || '',
            vod_director: filmData.director || '',
            vod_content: filmData.blurb || '',
            vod_score: filmData.doubanScore || '',
            vod_play_from: shows.join('$$$'),
            vod_play_url: play_urls.join('$$$'),
            type_name: filmData.vod_class || ''
        }]
    };
};

// 3. 搜索功能
const searchVod = async ({ page, quick, wd }) => {
    const pageNum = Math.max(1, parseInt(page) || 1);
    try {
        const response = await _http.get(`${shanYouMuXiConfig.host}/api/film/search`, {
            params: { keyword: wd, pageNum: pageNum, pageSize: 10 },
            headers: { ...shanYouMuXiConfig.headers, "Referer": shanYouMuXiConfig.host + "/" }
        });

        const list = (response.data?.data?.list || []).map(item => ({
            vod_id: strval(item.id),
            vod_name: item.name || '',
            vod_pic: item.cover || '',
            vod_remarks: item.updateStatus || '',
            vod_year: item.year || '',
            vod_area: item.area || '',
            vod_director: item.director || ''
        }));

        return {
            list,
            page: pageNum,
            pagecount: list.length >= 10 ? pageNum + 1 : pageNum,
            total: response.data?.data?.total || list.length
        };
    } catch (error) {
        return { list: [], page: pageNum, pagecount: 1, total: 0 };
    }
};

// 4. 分类列表
const getCategoryList = async ({ id, page, filters }) => {
    const pageNum = Math.max(1, parseInt(page) || 1);
    try {
        const response = await _http.get(`${shanYouMuXiConfig.host}/api/film/category/list`, {
            params: {
                area: filters?.area || '',
                categoryId: id,
                language: filters?.language || '',
                pageNum: pageNum,
                pageSize: 15,
                sort: filters?.sort || 'updateTime',
                year: filters?.year || ''
            },
            headers: { ...shanYouMuXiConfig.headers, "Referer": shanYouMuXiConfig.host + "/" }
        });

        const list = (response.data?.data?.list || []).map(item => ({
            vod_id: strval(item.id),
            vod_name: item.name || '',
            vod_pic: item.cover || '',
            vod_remarks: item.updateStatus || ''
        }));

        return {
            list,
            page: pageNum,
            pagecount: list.length >= 15 ? pageNum + 1 : pageNum,
            total: response.data?.data?.total || list.length
        };
    } catch (error) {
        return { list: [], page: pageNum, pagecount: 1, total: 0 };
    }
};

// 获取分类筛选配置
const getCategoryFilters = async (categoryId) => {
    const data = await fetch(`${shanYouMuXiConfig.host}/api/film/category/filter?categoryId=${encodeURIComponent(categoryId)}`, '/');
    if (!data || !data.data) return [];

    const filterData = data.data;
    const filters = [];

    if (filterData.areaOptions?.length) {
        filters.push({ key: 'area', name: '地区', value: [{ n: '全部', v: '' }, ...filterData.areaOptions.map(item => ({ n: item, v: item }))] });
    }
    if (filterData.yearOptions?.length) {
        filters.push({ key: 'year', name: '年份', value: [{ n: '全部', v: '' }, ...filterData.yearOptions.map(item => ({ n: item, v: item }))] });
    }
    if (filterData.languageOptions?.length) {
        filters.push({ key: 'language', name: '语言', value: [{ n: '全部', v: '' }, ...filterData.languageOptions.map(item => ({ n: item, v: item }))] });
    }
    if (filterData.sortOptions?.length) {
        filters.push({ key: 'sort', name: '排序', value: filterData.sortOptions.map(item => ({ n: item.label, v: item.value })) });
    }

    return filters;
};

// 5. 获取首页分类和筛选
const home = async ({ filter }) => {
    const data = await fetch(`${shanYouMuXiConfig.host}/api/category/top`, '/');
    const classes = [];
    const filters = {};

    if (data?.data && Array.isArray(data.data)) {
        for (const item of data.data) {
            const typeId = strval(item.id);
            classes.push({ type_id: typeId, type_name: item.name || '' });
            const categoryFilters = await getCategoryFilters(item.id);
            if (categoryFilters.length > 0) filters[typeId] = categoryFilters;
        }
    }

    return { class: classes, filters, list: [] };
};

// 6. 获取首页推荐
const getHomeRecommend = async () => {
    const data = await fetch(`${shanYouMuXiConfig.host}/api/film/category`, '/');
    const list = [];
    if (data?.data && Array.isArray(data.data)) {
        data.data.forEach(category => {
            (category.filmList || []).forEach(film => {
                list.push({
                    vod_id: strval(film.id),
                    vod_name: film.name || '',
                    vod_pic: film.cover || '',
                    vod_remarks: film.doubanScore || ''
                });
            });
        });
    }
    return list.slice(0, 30);
};

// 工具函数：转换为字符串
const strval = (value) => {
    return value === null || value === undefined ? '' : String(value);
};

// Base64解码工具
const decodeExt = (ext) => {
    if (!ext) return {};
    try {
        return JSON.parse(ext);
    } catch (e) {
        try {
            return JSON.parse(Buffer.from(ext, 'base64').toString('utf-8'));
        } catch (e2) {
            try {
                return JSON.parse(decodeURIComponent(ext));
            } catch (e3) {
                return {};
            }
        }
    }
};

// 模块元信息
const store = {
    init: false,
    meta: {
        key: "ShanYouMuXi",
        name: "山有木兮",
        type: 4,
        api: "/video/ShanYouMuXi",
        searchable: 1,
        quickSearch: 1,
        changeable: 0,
        filterable: 1
    },
    home: home,
    category: getCategoryList,
    detail: getDetail,
    search: searchVod,
    play: getPlayUrl
};

module.exports = async (app, opt) => {
    const log = app.log ? initLogger(app.log) : initLogger();

    app.get(store.meta.api, async (req, reply) => {
        const { t, ac, pg, ext, ids, play, wd, quick } = req.query;

        // 播放请求
        if (play) {
            return await store.play(play);
        }

        // 搜索请求
        if (wd) {
            return await store.search({ 
                page: parseInt(pg || "1"), 
                quick: quick === '1' || quick === 'true', 
                wd 
            });
        }

        // 分类列表请求
        if (ac === "detail" && t) {
            return await store.category({ 
                id: t, 
                page: parseInt(pg || "1"), 
                filters: ext ? decodeExt(ext) : {} 
            });
        }

        // 详情请求
        if (ac === "detail" && ids) {
            const idArray = ids.split(",").map(id => id.trim()).filter(Boolean);
            if (idArray.length > 0) {
                return await store.detail(idArray[0]);
            }
            return { list: [] };
        }

        // 首页分类和筛选
        if (!ac || ac === "home") {
            const result = await store.home({ filter: true });
            if (!ac) {
                result.list = await getHomeRecommend();
            }
            return result;
        }

        return { list: [], class: [] };
    });

    opt.sites.push(store.meta);
};