/**
 * 嘀嗒影视 爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-17
 * 发布页 https://www.didahd.pro/
 */

const baseUrl = 'https://www.didahd.pro/';

/**
 * 初始化配置
 */
async function init(cfg) {
    return {
        webview: {
            debug: true,
            showWebView: true,
            widthPercent: 80,
            heightPercent: 60,
            keyword: '',
            returnType: 'dom',
            timeout: 30,
            blockImages: true,
            enableJavaScript: true,
            header: { 'Referer': baseUrl },
            blockList: [
                "*.ico*",
                "*.png*",
                "*.jpg*",
                "*.jpeg*",
                "*.gif*",
                "*.webp*",
                "*.css*"
            ]
        }
    };
}

/**
 * 首页分类
 */
async function homeContent(filter) {

    const filterConfig = {
        class: [
            { type_id: "1", type_name: "电影" },
            { type_id: "2", type_name: "电视剧" },
            { type_id: "4", type_name: "动漫" }
        ],
        filters: {
            "1": [
                { key: "type",  name: "按类型",  value: [ {n:"全部",v:""}, {n:"动作片",v:"dongzuopian"}, {n:"剧情片",v:"juqingpian"}, {n:"冒险片",v:"maoxianpian"}, {n:"惊悚片",v:"jingsongpian"}, {n:"喜剧片",v:"xijupian"}, {n:"爱情片",v:"aiqingpian"}, {n:"科幻片",v:"kehuanpian"}, {n:"战争片",v:"zhanzhengpian"}, {n:"警匪片",v:"jingfeipian"}, {n:"犯罪片",v:"fanzuipian"}, {n:"恐怖片",v:"kongbupian"}, {n:"悬疑片",v:"xuanyipian"}, {n:"灾难片",v:"zainanpian"}, {n:"奇幻片",v:"qihuanpian"}, {n:"动画片",v:"donghuapian"}, {n:"其他片",v:"qitapian"} ] },
                { key: "class", name: "按剧情",  value: [ {n:"全部",v:""}, {n:"喜剧",v:"喜剧"}, {n:"爱情",v:"爱情"}, {n:"恐怖",v:"恐怖"}, {n:"动作",v:"动作"}, {n:"科幻",v:"科幻"}, {n:"剧情",v:"剧情"}, {n:"战争",v:"战争"}, {n:"警匪",v:"警匪"}, {n:"犯罪",v:"犯罪"}, {n:"动画",v:"动画"}, {n:"奇幻",v:"奇幻"}, {n:"武侠",v:"武侠"}, {n:"冒险",v:"冒险"}, {n:"枪战",v:"枪战"}, {n:"悬疑",v:"悬疑"}, {n:"惊悚",v:"惊悚"}, {n:"经典",v:"经典"}, {n:"青春",v:"青春"}, {n:"文艺",v:"文艺"}, {n:"微电影",v:"微电影"}, {n:"古装",v:"古装"}, {n:"历史",v:"历史"}, {n:"运动",v:"运动"}, {n:"农村",v:"农村"}, {n:"儿童",v:"儿童"}, {n:"网络电影",v:"网络电影"} ] },
                { key: "area",  name: "按地区",  value: [ {n:"全部",v:""}, {n:"大陆",v:"大陆"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"}, {n:"美国",v:"美国"}, {n:"法国",v:"法国"}, {n:"英国",v:"英国"}, {n:"日本",v:"日本"}, {n:"韩国",v:"韩国"}, {n:"德国",v:"德国"}, {n:"泰国",v:"泰国"}, {n:"印度",v:"印度"}, {n:"意大利",v:"意大利"}, {n:"西班牙",v:"西班牙"}, {n:"加拿大",v:"加拿大"}, {n:"其他",v:"其他"} ] },
                { key: "year",  name: "按年份",  value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"} ] },
                { key: "lang",  name: "按语言",  value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"法语",v:"法语"}, {n:"德语",v:"德语"}, {n:"其它",v:"其它"} ] },
                { key: "sort",  name: "按排序",  value: [ {n:"时间",v:"time"}, {n:"人气",v:"hits"}, {n:"评分",v:"score"} ] }
            ],
            "2": [
                { key: "type",  name: "按类型",  value: [ {n:"全部",v:""}, {n:"国产剧",v:"guochanju"}, {n:"港台剧",v:"gangtaiju"}, {n:"日韩剧",v:"rihanju"}, {n:"欧美剧",v:"oumeiju"}, {n:"泰国剧",v:"taiguoju"}, {n:"其他剧",v:"qitaju"} ] },
                { key: "class", name: "按剧情",  value: [ {n:"全部",v:""}, {n:"古装",v:"古装"}, {n:"战争",v:"战争"}, {n:"青春偶像",v:"青春偶像"}, {n:"喜剧",v:"喜剧"}, {n:"家庭",v:"家庭"}, {n:"犯罪",v:"犯罪"}, {n:"动作",v:"动作"}, {n:"奇幻",v:"奇幻"}, {n:"剧情",v:"剧情"}, {n:"历史",v:"历史"}, {n:"经典",v:"经典"}, {n:"乡村",v:"乡村"}, {n:"情景",v:"情景"}, {n:"商战",v:"商战"}, {n:"网剧",v:"网剧"}, {n:"其他",v:"其他"} ] },
                { key: "area",  name: "按地区",  value: [ {n:"全部",v:""}, {n:"内地",v:"内地"}, {n:"韩国",v:"韩国"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"}, {n:"日本",v:"日本"}, {n:"美国",v:"美国"}, {n:"泰国",v:"泰国"}, {n:"英国",v:"英国"}, {n:"新加坡",v:"新加坡"}, {n:"其他",v:"其他"} ] },
                { key: "year",  name: "按年份",  value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"} ] },
                { key: "lang",  name: "按语言",  value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"其它",v:"其它"} ] },
                { key: "sort",  name: "按排序",  value: [ {n:"时间",v:"time"}, {n:"人气",v:"hits"}, {n:"评分",v:"score"} ] }
            ],
            "4": [
                { key: "type",  name: "按类型",  value: [ {n:"全部",v:""}, {n:"日韩动漫",v:"rihandongman"}, {n:"国产动漫",v:"guochandongman"}, {n:"欧美动漫",v:"oumeidongman"}, {n:"港台动漫",v:"gangtaidongman"}, {n:"其他动漫",v:"qitadongman"} ] },
                { key: "class", name: "按剧情",  value: [ {n:"全部",v:""}, {n:"情感",v:"情感"}, {n:"科幻",v:"科幻"}, {n:"热血",v:"热血"}, {n:"推理",v:"推理"}, {n:"搞笑",v:"搞笑"}, {n:"冒险",v:"冒险"}, {n:"萝莉",v:"萝莉"}, {n:"校园",v:"校园"}, {n:"动作",v:"动作"}, {n:"机战",v:"机战"}, {n:"运动",v:"运动"}, {n:"战争",v:"战争"}, {n:"少年",v:"少年"}, {n:"少女",v:"少女"}, {n:"社会",v:"社会"}, {n:"原创",v:"原创"}, {n:"亲子",v:"亲子"}, {n:"益智",v:"益智"}, {n:"励志",v:"励志"}, {n:"其他",v:"其他"} ] },
                { key: "area",  name: "按地区",  value: [ {n:"全部",v:""}, {n:"国产",v:"国产"}, {n:"日本",v:"日本"}, {n:"欧美",v:"欧美"}, {n:"其他",v:"其他"} ] },
                { key: "year",  name: "按年份",  value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"} ] },
                { key: "lang",  name: "按语言",  value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"其它",v:"其它"} ] },
                { key: "sort",  name: "按排序",  value: [ {n:"时间",v:"time"}, {n:"人气",v:"hits"}, {n:"评分",v:"score"} ] }
            ]
        }
    };


    return filterConfig;
}

/**
 * 首页推荐视频
 */
async function homeVideoContent() {
    const document = await Java.wvOpen(baseUrl + '/');
    const videos = parseVideoList(document);
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
    const type = extend.type || tid;
    const lang = extend.lang || '';

    // console.log("筛选参数:", extend, `type=${type}, area=${area}, year=${year}, cat=${cat}, sort=${sort}, lang=${lang}`);
    // const document = await Java.wvOpen(`${baseUrl}/list/${type||tid}-${area}-${sort}-${cat}-${lang}----${pg}---${year}.html`);
    const document = await Java.wvOpen(`${baseUrl}/show/${tid}-${area}-${sort}-${type}-${lang}-${letter}---${pg}---${year}.html`);
    const videos = parseVideoList(document);
    const getPages = document.querySelector("ul > li.active.num").outerText;
    const pages = getPages.split('/');
    return { code: 1, msg: "数据列表", list: videos, page: pages[0], pagecount: pages[1], limit: 12, total: pages[1] * 12 };
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
function parseVideoList(document) {
    const boxes = Array.from(document.querySelectorAll('.stui-vodlist__box'));
    const list = boxes.map(box => {
        const titleEl   = box.querySelector('.title a');
        const thumbEl   = box.querySelector('.stui-vodlist__thumb');
        const remarksEl = box.querySelector('.pic-text');

        // 处理 vod_id
        let vodId = titleEl?.getAttribute('href') || '';
        if (vodId && !vodId.startsWith('http')) {
            vodId = baseUrl + (vodId.startsWith('/') ? '' : '/') + vodId;
        }

        return {
            vod_name:   titleEl?.title || titleEl?.textContent || '',
            vod_pic:    thumbEl?.getAttribute('data-original') ||
                        thumbEl?.style.backgroundImage?.match(/url\(["']?([^"')]+)["']?\)/)?.[1] || '',
            vod_remarks: remarksEl?.textContent || '',
            vod_id:    vodId,
            vod_actor: (() => {
                const textEl  = box.querySelector('.text');
                const comment = textEl?.previousSibling;
                return comment?.nodeType === 8 ? comment.textContent.trim() : '';
            })()
        };
    });

    return list;
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


/* ---------------- 导出对象 ---------------- */
const spider = { init, homeContent, homeVideoContent, categoryContent, detailContent, searchContent, playerContent, action };
spider;
