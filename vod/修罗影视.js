/**
 * 修罗影视 爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-17
 * 发布页 https://xlys.me/
 *
 * @config
 * debug: true
//  * showWebView: true
 * percent: 80,60
 * returnType: dom
 * timeout: 30
 * blockImages: true
 * blockList: *.[ico|png|jpeg|jpg|gif|webp]*|*.css|*rosfky.cn*|*zzz*|*3s3peo*|*google*|*.js*
 *
 */

const baseUrl = 'https://www.xlys02.com';

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
            {type_id: "dongzuo", type_name: "动作"},
            {type_id: "aiqing", type_name: "爱情"},
            {type_id: "xiju", type_name: "喜剧"},
            {type_id: "kehuan", type_name: "科幻"},
            {type_id: "kongbu", type_name: "恐怖"},
            {type_id: "zhanzheng", type_name: "战争"},
            {type_id: "wuxia", type_name: "武侠"},
            {type_id: "mohuan", type_name: "魔幻"},
            {type_id: "juqing", type_name: "剧情"},
            {type_id: "donghua", type_name: "动画"},
            {type_id: "jingsong", type_name: "惊悚"},
            {type_id: "3D", type_name: "3D"},
            {type_id: "zainan", type_name: "灾难"},
            {type_id: "xuanyi", type_name: "悬疑"},
            {type_id: "jingfei", type_name: "警匪"},
            {type_id: "wenyi", type_name: "文艺"},
            {type_id: "qingchun", type_name: "青春"},
            {type_id: "maoxian", type_name: "冒险"},
            {type_id: "fanzui", type_name: "犯罪"},
            {type_id: "jilu", type_name: "纪录"},
            {type_id: "guzhuang", type_name: "古装"},
            {type_id: "qihuan", type_name: "奇幻"},
            {type_id: "guoyu", type_name: "国语"},
            {type_id: "zongyi", type_name: "综艺"},
            {type_id: "lishi", type_name: "历史"},
            {type_id: "yundong", type_name: "运动"},
            {type_id: "yuanchuang", type_name: "原创压制"},
            {type_id: "meiju", type_name: "美剧"},
            {type_id: "hanju", type_name: "韩剧"},
            {type_id: "guoju", type_name: "国产电视剧"},
            {type_id: "riju", type_name: "日剧"},
            {type_id: "yingju", type_name: "英剧"},
            {type_id: "deju", type_name: "德剧"},
            {type_id: "eju", type_name: "俄剧"},
            {type_id: "baju", type_name: "巴剧"},
            {type_id: "jiaju", type_name: "加剧"},
            {type_id: "spanish", type_name: "西剧"},
            {type_id: "yidaliju", type_name: "意大利剧"},
            {type_id: "taiju", type_name: "泰剧"},
            {type_id: "gangtaiju", type_name: "港台剧"},
            {type_id: "faju", type_name: "法剧"},
            {type_id: "aoju", type_name: "澳剧"},
            {type_id: "duanju", type_name: "短剧"}
        ],
        filters: {}
    };

    const commonFilters = [
        {key: "type", name: "资源分类", value: [{n: "全部", v: ""}, {n: "电影", v: "0"}, {n: "电视剧", v: "1"}]},
        {key: "area", name: "制片地区", value: [{n: "全部", v: ""}, {n: "中国大陆", v: "中国大陆"}, {n: "中国香港", v: "中国香港"}, {n: "中国台湾", v: "中国台湾"}, {n: "美国", v: "美国"}, {n: "英国", v: "英国"}, {n: "日本", v: "日本"}, {n: "韩国", v: "韩国"}, {n: "法国", v: "法国"}, {n: "印度", v: "印度"}, {n: "德国", v: "德国"}, {n: "西班牙", v: "西班牙"}, {n: "意大利", v: "意大利"}, {n: "澳大利亚", v: "澳大利亚"}, {n: "比利时", v: "比利时"}, {n: "瑞典", v: "瑞典"}, {n: "荷兰", v: "荷兰"}, {n: "丹麦", v: "丹麦"}, {n: "加拿大", v: "加拿大"}, {n: "俄罗斯", v: "俄罗斯"}]},
        {key: "year", name: "上映时间", value: [{n: "全部", v: ""}, {n: "2025", v: "2025"}, {n: "2024", v: "2024"}, {n: "2023", v: "2023"}, {n: "2022", v: "2022"}, {n: "2021", v: "2021"}, {n: "2020", v: "2020"}, {n: "2019", v: "2019"}, {n: "2018", v: "2018"}, {n: "2017", v: "2017"}, {n: "2016", v: "2016"}, {n: "2015", v: "2015"}, {n: "2014", v: "2014"}, {n: "2013", v: "2013"}, {n: "2012", v: "2012"}, {n: "2011", v: "2011"}, {n: "2010", v: "2010"}, {n: "2009", v: "2009"}, {n: "2008", v: "2008"}, {n: "2007", v: "2007"}, {n: "2006", v: "2006"}, {n: "2005", v: "2005"}, {n: "2004", v: "2004"}, {n: "2003", v: "2003"}, {n: "2002", v: "2002"}]},
        {key: "order", name: "影视排序", value: [{n: "默认", v: ""}, {n: "更新时间", v: "0"}, {n: "豆瓣评分", v: "1"}]}
    ];

    filterConfig.class.forEach(item => {
        filterConfig.filters[item.type_id] = commonFilters;
    });

    return filterConfig;
}

/**
 * 首页推荐视频
 */
async function homeVideoContent() {
    const document = await Java.wvOpen(`${baseUrl}`);  // 使用模板字符串
    const videos = parseVideoList(document);
    return { list: videos };
}

/**
 * 分类内容
 */
async function categoryContent(tid, pg, filter, extend) {

    // https://www.xlys02.com/s/aiqing?type=1&area=地区&year=2025&order=0
    await Java.wvOpen(`${baseUrl}/s/${tid}/${pg}?[type=${extend?.type}]&[area=${extend?.area}]&[year=${extend?.year}]&[order=${extend?.order}]`);
    const videos = parseVideoList(document);

    const pagecount = parseInt(Array.from(document.querySelectorAll('a.page-link')).find(el => el.textContent.includes('尾页'))?.href?.match(/\/(\d+)\?/)?.[1] || "1");
    return { code: 1, msg: "数据列表", page: pg, pagecount: 10000, limit: videos.length, total: videos.length * 10000, list: videos };
}

/**
 * 详情页
 */
async function detailContent(ids) {
	// Java.showWebView();
    const document = await Java.wvOpen(ids[0]);
    const list = parseDetailPage(document);
    return { code: 1, msg: "数据列表", page: 1, pagecount: 1, limit: 1, total: 1, list };
}

/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
    let res = await Java.req(`${baseUrl}/search/${key}----------${pg}---.html`);
    const videos = parseVideoList(res.doc);
    let pages = [1, 1];
    let total = videos.length;
    try {
        const getPages = res.doc.querySelector("ul > li.active.num").outerText;
        pages = getPages.split('/');
        total = parseInt(pages[1]) * 12;
    } catch (e) {}
    return { code: 1, msg: "数据列表", list: videos, page: pages[0], pagecount: pages[1], limit: 12, total };
}

/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
    return { url: id, parse: 1 };
}

/**
 * action
 */
async function action(actionStr) {
    try {
        const params = JSON.parse(actionStr);
        console.log("action params:", params);
    } catch (e) {
        console.log("action is not JSON, treat as string");
    }
    return;
}


/* ---------------- 工具函数 ---------------- */

/**
 * 提取视频列表
 */
function parseVideoList() {
    const vods = [];
    document.querySelectorAll('.row-cards .card-sm').forEach(item => {
        const link = item.querySelector('a.cover');
        const img = item.querySelector('img');
        const badge = item.querySelector('.badge');
        const date = item.querySelector('.text-muted');
        vods.push({
            vod_id: link?.getAttribute('href') || '',
            vod_name: item.querySelector('.card-title')?.textContent?.trim() || '',
            vod_pic: img?.getAttribute('data-src') || img?.getAttribute('src') || '',
            vod_remarks: badge?.textContent?.trim() || '',
            vod_year: date?.textContent?.trim() || ''
        });
    });
    return vods;
}


/**
 * 解析详情页
 */
function parseDetailPage(document) {
    const title = document.querySelector('.stui-content__detail .title')?.textContent.trim() || '';
    const vod_pic = document.querySelector('.stui-content__thumb img')?.src || '';
    const info = document.querySelectorAll('.stui-content__detail .data');

    const typeMatch = info[0]?.textContent.match(/类型：([^/]+)\s*\/\s*地区：([^/]+)\s*\/\s*年份：(\d+)/) || [];
    const type_name = typeMatch[1] || '', vod_area = typeMatch[2] || '', vod_year = typeMatch[3] || '';
    const vod_actor = info[1]?.textContent.replace('主演：', '').trim() || '';
    const vod_director = info[2]?.textContent.replace('导演：', '').trim() || '';
    const vod_remarks = info[3]?.textContent.replace('更新：', '').trim() || '';
    const vod_content = document.querySelector('.detail-content')?.textContent.trim() ||
                        document.querySelector('.detail-sketch')?.textContent.trim() || '';

    // 播放线路
    const head = document.querySelector('.stui-vodlist__head h3');
    const ul = document.querySelector('.stui-content__playlist');
    const episodes = ul ? Array.from(ul.querySelectorAll('a')).map(a =>
        `${a.textContent.trim()}$${baseUrl + a.getAttribute('href')}`) : [];
    const vod_play_from = head ? head.textContent.trim().replace('在线播放', '线路') : '';
    const vod_play_url = episodes.join('#');

    return [{
        vod_id: window.location.pathname.replace(/[^\w]/g, '_'),
        vod_name: title,
        vod_pic: vod_pic,
        vod_remarks: vod_remarks,
        vod_year: vod_year,
        vod_actor: vod_actor,
        vod_director: vod_director,
        vod_area: vod_area,
        vod_lang: vod_area.includes('大陆') ? '国语' : '其他',
        vod_content: vod_content,
        vod_play_from: vod_play_from,
        vod_play_url: vod_play_url
    }];
}

