/**
 * 3Q影视 爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-17
 * 发布页 https://qqqys.com
 * 
 * @config
//  * debug: true
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
    let res = Java.req(baseUrl);
    if (res.error) return Result.error('获取数据失败:'  + res.error);
    const doc = res.doc;
    const videos = parseVideoList(doc);

    return { list: videos };
}

/**
 * 分类内容
 */
async function categoryContent(tid, pg, filter, extend) {
    const area = extend.area || '';
    const year = extend.year || '';
    const cat = extend.class || '';
    const sort = extend.sort || '';
    let res = Java.req(`${baseUrl}/api.php/filter/vod?type_name=${tid}&class=${cat}&year=${year}&area=${area}&sort=${sort}&page=${pg}&limit=24`);
    if (res.error) return Result.error('获取数据失败:'  + res.error);
    const result = JSON.parse(res.body);
    result.list = result.data;
    delete result.data;
    return result;
}

/**
 * 详情页
 */
async function detailContent(ids) {
    let res = Java.req(`${baseUrl}/vd/${ids[0]}.html`);
    if (res.error) return Result.error('详情获取失败:'  + res.error);
    let j = Java.req(`${baseUrl}/api.php/internal/search_aggregate?vod_id=${ids[0]}`);
    const jsonData = JSON.parse(j.body);
    const vods = parseDetailPage(res.doc, jsonData, ids[0]);
    return { code: 1, msg: "数据列表", page: 1, pagecount: 1, limit: 1, total: 1, list: vods };
}

/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
    let res = await Java.req(`${baseUrl}/vodsearch/${key}--/page/${pg}.html`);
    const vods = [];
    const items = res.doc.querySelectorAll('div.p-2 > div');
    
    items.forEach(item => {
        const link = item.querySelector('a[href*="/vd/"]');
        if (!link) return;
        
        const href = link.getAttribute('href');
        const vod_id = href.match(/\/vd\/(\d+)\.html/)?.[1] || '';
        
        const nameEl = item.querySelector('.text-\\[16px\\] span strong') || 
                      item.querySelector('.text-\\[16px\\] strong') ||
                      item.querySelector('div.ml-\\[105px\\] strong');
        const vod_name = nameEl?.textContent?.trim() || '';
        
        const img = item.querySelector('img[data-original]');
        const vod_pic = img?.getAttribute('data-original') || '';
        
        const remarkDiv = item.querySelector('div[class*="bottom-0"][class*="right-0"]') ||
                         item.querySelector('div[style*="gradient"]');
        const vod_remarks = remarkDiv?.textContent?.trim() || '';
        
        if (vod_id && vod_name) {
            vods.push({
                vod_id: vod_id,
                vod_name: vod_name,
                vod_pic: vod_pic,
                vod_remarks: vod_remarks
            });
        }
    });
    
    const totalText = document.querySelector('.mac_total')?.textContent || '0';
    const total = parseInt(totalText) || vods.length;
    const pagecount = Math.ceil(total / 15);
    
    const pageMatch = window.location.href.match(/page\/(\d+)\.html/);
    const page = pageMatch ? parseInt(pageMatch[1]) : 1;
    
    return { 
        code: 1, 
        msg: "数据列表", 
        list: vods, 
        page: page, 
        pagecount: pagecount, 
        limit: 15, 
        total: total 
    };
}

/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
    return { url: id, parse: 0 };
}


/* ---------------- 工具函数 ---------------- */

/**
 * 提取视频列表
 */
function parseVideoList(document) {
    const vods = [];
    const items = document.querySelectorAll('.grid-cols-3 > div');

    items.forEach(item => {
        const link = item.querySelector('a');
        const img = item.querySelector('img');
        const remarkDiv = item.querySelector('.absolute.right-0.bottom-0.left-0');
        
        let vod_id = '';
        const href = link?.getAttribute('href') || '';
        if (href.includes('/vd/')) {
            vod_id = href.match(/\/vd\/(\d+)\.html/)?.[1] || '';
        } else if (href.includes('.html')) {
            vod_id = href.match(/(\d+)\.html/)?.[1] || '';
        }
        
        const vod = {
            vod_id: vod_id,
            vod_name: link?.getAttribute('title') || '',
            vod_pic: img?.getAttribute('data-original') || '',
            vod_remarks: remarkDiv?.textContent?.trim() || '',
        };
        
        vods.push(vod);
    });
    
    return vods;
}

/**
 * 解析详情页
 */
function parseDetailPage(doc, jsonData, vod_id) {
    const vod_name = doc.querySelector('.module-info-heading h1')?.textContent?.trim() || '';
    const vod_pic = doc.querySelector('img[data-original]')?.getAttribute('data-original') || '';
    const vod_content = doc.querySelector('.module-info-content .line-clamp-5 p')?.textContent?.trim() || '';

    const infoDivs = doc.querySelectorAll('.module-info-heading > div > div');
    const vod_remark = Array.from(infoDivs).map(div => 
        div.textContent.replace(/[\t\n]/g, '').trim()
    ).filter(text => text).join(' / ');

    const vod_play_from = jsonData.data?.map(item => item.site_name).filter(Boolean).join('$$$') || '';
    const vod_play_url = jsonData.data?.map(item => 
        item.vod_play_url?.replace(/\t+/g, '').trim()
    ).filter(Boolean).join('$$$') || '';

    const flexItems = doc.querySelectorAll('.module-info-content .flex');
    let vod_director = '';
    let vod_actor = '';
    
    flexItems.forEach(item => {
        const span = item.querySelector('span');
        if (span?.textContent.includes('导演')) {
            const directorLinks = item.querySelectorAll('a');
            if (directorLinks.length > 0) {
                const vod_director = Array.from(directorLinks).map(link => link.textContent.trim());
            }
        } else if (span?.textContent.includes('主演')) {
            const actorLinks = item.querySelectorAll('a');
            if (actorLinks.length > 0) {
                const vod_actor = Array.from(actorLinks).map(link => link.textContent.trim());
            }
        }
    });

    return [{
        vod_id: vod_id,
        vod_name: vod_name,
        vod_pic: vod_pic,
        vod_director: vod_director,
        vod_actor: vod_actor,
        vod_remark: vod_remark,
        vod_content: vod_content,
        vod_play_from: vod_play_from,
        vod_play_url: vod_play_url
    }];
}