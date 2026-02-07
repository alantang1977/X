/**
 * 3Q影视 爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-17
 * 发布页 https://qqqys.com
 * 
 * @config
 * debug: false
 */

const baseUrl = 'https://qqqys.com';



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

    const filterConfig = {
        class: [
            { type_id: "电影", type_name: "电影" },
            { type_id: "剧集", type_name: "剧集" },
            { type_id: "动漫", type_name: "动漫" },
            { type_id: "综艺", type_name: "综艺" }
        ],
        filters: {
            "电影": [
                { key: "class", name: "类型", value: [ {n:"全部",v:""}, {n:"动作",v:"动作"}, {n:"喜剧",v:"喜剧"}, {n:"爱情",v:"爱情"}, {n:"科幻",v:"科幻"}, {n:"恐怖",v:"恐怖"}, {n:"悬疑",v:"悬疑"}, {n:"犯罪",v:"犯罪"}, {n:"战争",v:"战争"}, {n:"动画",v:"动画"}, {n:"冒险",v:"冒险"}, {n:"历史",v:"历史"}, {n:"灾难",v:"灾难"}, {n:"纪录",v:"纪录"}, {n:"剧情",v:"剧情"} ] },
                { key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"大陆",v:"大陆"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"}, {n:"美国",v:"美国"}, {n:"日本",v:"日本"}, {n:"韩国",v:"韩国"}, {n:"泰国",v:"泰国"}, {n:"印度",v:"印度"}, {n:"英国",v:"英国"}, {n:"法国",v:"法国"}, {n:"德国",v:"德国"}, {n:"加拿大",v:"加拿大"}, {n:"西班牙",v:"西班牙"}, {n:"意大利",v:"意大利"}, {n:"澳大利亚",v:"澳大利亚"} ] },
                { key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015-2011",v:"2015-2011"}, {n:"2010-2000",v:"2010-2000"}, {n:"90年代",v:"90年代"}, {n:"80年代",v:"80年代"}, {n:"更早",v:"更早"} ] },
                { key: "sort", name: "排序", value: [ {n:"人气",v:"hits"}, {n:"最新",v:"time"}, {n:"评分",v:"score"}, {n:"年份",v:"year"} ] }
            ],
            "剧集": [
                { key: "class", name: "类型", value: [ {n:"全部",v:""}, {n:"爱情",v:"爱情"}, {n:"古装",v:"古装"}, {n:"武侠",v:"武侠"}, {n:"历史",v:"历史"}, {n:"家庭",v:"家庭"}, {n:"喜剧",v:"喜剧"}, {n:"悬疑",v:"悬疑"}, {n:"犯罪",v:"犯罪"}, {n:"战争",v:"战争"}, {n:"奇幻",v:"奇幻"}, {n:"科幻",v:"科幻"}, {n:"恐怖",v:"恐怖"} ] },
                { key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"大陆",v:"大陆"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"}, {n:"美国",v:"美国"}, {n:"日本",v:"日本"}, {n:"韩国",v:"韩国"}, {n:"泰国",v:"泰国"}, {n:"英国",v:"英国"} ] },
                { key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020-2016",v:"2020-2016"}, {n:"2015-2011",v:"2015-2011"}, {n:"2010-2000",v:"2010-2000"}, {n:"更早",v:"更早"} ] },
                { key: "sort", name: "排序", value: [ {n:"人气",v:"hits"}, {n:"最新",v:"time"}, {n:"评分",v:"score"}, {n:"年份",v:"year"} ] }
            ],
            "动漫": [
                { key: "class", name: "类型", value: [ {n:"全部",v:""}, {n:"冒险",v:"冒险"}, {n:"奇幻",v:"奇幻"}, {n:"科幻",v:"科幻"}, {n:"武侠",v:"武侠"}, {n:"悬疑",v:"悬疑"} ] },
                { key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"大陆",v:"大陆"}, {n:"日本",v:"日本"}, {n:"欧美",v:"欧美"} ] },
                { key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"更早",v:"更早"} ] },
                { key: "sort", name: "排序", value: [ {n:"人气",v:"hits"}, {n:"最新",v:"time"}, {n:"评分",v:"score"}, {n:"年份",v:"year"} ] }
            ],
            "综艺": [
                { key: "class", name: "类型", value: [ {n:"全部",v:""}, {n:"真人秀",v:"真人秀"}, {n:"音乐",v:"音乐"}, {n:"脱口秀",v:"脱口秀"}, {n:"歌舞",v:"歌舞"}, {n:"爱情",v:"爱情"} ] },
                { key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"大陆",v:"大陆"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"}, {n:"美国",v:"美国"}, {n:"日本",v:"日本"}, {n:"韩国",v:"韩国"} ] },
                { key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"更早",v:"更早"} ] },
                { key: "sort", name: "排序", value: [ {n:"人气",v:"hits"}, {n:"最新",v:"time"}, {n:"评分",v:"score"}, {n:"年份",v:"year"} ] }
            ]
        }
    };

    return filterConfig;
}

/**
 * 首页推荐视频
 */
async function homeVideoContent() {
    let res = Java.req(`${baseUrl}/api.php/web/index/home`);
    if (res.error) return Result.error('获取首页失败:' + res.error);
    
    const jsonData = JSON.parse(res.body);
    if (!jsonData.data || !jsonData.data.categories) return { list: [] };
    
    const videos = [];
    jsonData.data.categories.forEach(category => {
        if (category.videos && Array.isArray(category.videos)) {
            category.videos.forEach(vod => {
                videos.push({
                    vod_id: vod.vod_id ? vod.vod_id.toString() : '',
                    vod_name: vod.vod_name || '',
                    vod_pic: vod.vod_pic || '',
                    vod_remarks: vod.vod_remarks || ''
                });
            });
        }
    });
    
    return { list: videos };
}

/**
 * 分类内容
 */
async function categoryContent(tid, pg, filter, extend) {
    const area = extend.area || '';
    const year = extend.year || '';
    const cat = extend.class || '';
    const sort = extend.sort || 'hits';
    
    let url = `${baseUrl}/api.php/web/filter/vod?type_name=${encodeURIComponent(tid)}&page=${pg}&sort=${sort}`;
    if (cat) url += `&class=${encodeURIComponent(cat)}`;
    if (area) url += `&area=${encodeURIComponent(area)}`;
    if (year) url += `&year=${encodeURIComponent(year)}`;
    
    let res = Java.req(url);
    if (res.error) return Result.error('获取数据失败:' + res.error);
    
    const result = JSON.parse(res.body);
    const list = [];
    
    if (result.data && Array.isArray(result.data)) {
        result.data.forEach(vod => {
            list.push({
                vod_id: vod.vod_id ? vod.vod_id.toString() : '',
                vod_name: vod.vod_name || '',
                vod_pic: vod.vod_pic || '',
                vod_remarks: vod.vod_remarks || ''
            });
        });
    }
    
    return { 
        code: 1, 
        msg: "数据列表", 
        list: list, 
        page: parseInt(pg), 
        pagecount: result.pageCount || 1, 
        limit: 24, 
        total: result.total || list.length 
    };
}

/**
 * 详情页
 */
async function detailContent(ids) {
    const vod_id = ids[0];
    
    let mainRes = await Java.req(`${baseUrl}/api.php/web/vod/get_detail?vod_id=${vod_id}`);
    
    if (mainRes.error) return Result.error('详情获取失败:' + mainRes.error);
    
    const mainData = JSON.parse(mainRes.body);
    if (!mainData.data || mainData.data.length === 0) return { list: [] };
    
    const vodData = mainData.data[0];
    const vodplayer = mainData.vodplayer || [];
    
    const playFromList = [];
    const playUrlList = [];

    if (vodData.vod_play_from && vodData.vod_play_url) {
        const raw_shows = vodData.vod_play_from.split('$$$');
        const raw_urls_list = vodData.vod_play_url.split('$$$');
        
        for (let i = 0; i < raw_shows.length; i++) {
            let show_code = raw_shows[i];
            let player = vodplayer.find(p => p.from === show_code);
            if (!player) continue;
            
            let lineName = player.show || show_code;
            let urls = [];
            let items = raw_urls_list[i].split('#');
            
            for (let j = 0; j < items.length; j++) {
                if (items[j].includes('$')) {
                    let [name, url_val] = items[j].split('$');
                    urls.push(`${name}$${lineName}@@${show_code}@@qqqparse@@${vod_id}@@${j + 1}@@${url_val}`);
                }
            }
            
            if (urls.length > 0) {
                playFromList.push(lineName);
                playUrlList.push(urls.join('#'));
            }
        }
    }
    
    return { 
        code: 1, 
        msg: "数据列表", 
        page: 1, 
        pagecount: 1, 
        limit: 1, 
        total: 1, 
        list: [{
            vod_id: vod_id,
            vod_name: vodData.vod_name || '',
            vod_pic: vodData.vod_pic || '',
            vod_content: vodData.vod_blurb || '',
            vod_director: vodData.vod_director || '',
            vod_actor: vodData.vod_actor || '',
            vod_year: vodData.vod_year || '',
            vod_area: vodData.vod_area || '',
            vod_class: vodData.vod_class || '',
            vod_remarks: vodData.vod_remarks || '',
            vod_play_from: playFromList.join('$$$'),
            vod_play_url: playUrlList.join('$$$')
        }] 
    };
}

/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
    let url = `${baseUrl}/api.php/web/search/index?wd=${encodeURIComponent(key)}&page=${pg}`;
    let res = await Java.req(url);
    
    if (res.error) return Result.error('搜索失败:' + res.error);
    
    const result = JSON.parse(res.body);
    const list = [];
    
    if (result.data && Array.isArray(result.data)) {
        result.data.forEach(vod => {
            list.push({
                vod_id: vod.vod_id ? vod.vod_id.toString() : '',
                vod_name: vod.vod_name || '',
                vod_pic: vod.vod_pic || '',
                vod_remarks: vod.vod_remarks || ''
            });
        });
    }
    
    return { 
        code: 1, 
        msg: "数据列表", 
        list: list, 
        page: parseInt(pg), 
        pagecount: result.pageCount || 1, 
        limit: 15, 
        total: result.total || list.length 
    };
}

/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
    console.log('播放请求:', { flag, id });

    if (id.includes('@@')) {
        const parts = id.split('@@');
        
        if (parts.length >= 6) {
            const lineName = parts[0];
            const siteId = parts[1];
            const mode = parts[2];
            const mediaId = parts[3];
            const nid = parts[4];
            const rawUrl = parts[5];
            
            if (mode === 'direct') {
                console.log('direct模式，直接播放:', rawUrl);
                return { url: rawUrl, parse: 0 };
            }

            if (mode === '360parse' || mode === 'qqqparse') {
                const finalUrl = `${baseUrl}/play/${mediaId}#sid=${siteId}&nid=${nid}`;
                return { 
                    parse: 1, 
                    url: finalUrl, 
                    header: { 'User-Agent': 'Mozilla/5.0' } 
                };
            }
        }
    }
    
    const [vodFrom, ...urlParts] = id.split(':');
    
    if (vodFrom === 'http' || vodFrom === 'https') {
        return { url: id, parse: 0 };
    }
    const url = urlParts.join(':');
    return { url: url, parse: 0 };
}