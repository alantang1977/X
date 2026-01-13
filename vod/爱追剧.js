/**
 * 爱追剧(aizju)爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-20
 * 发布页 https://www.aizju.com
 * @config
//  * debug: true
//  * showWebView: true
 * percent: 80,60
 * returnType: dom
 * timeout: 30
 *
 */


const baseUrl = 'https://www.aizju.com';

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
			{ type_id: "1", type_name: "电影" },
			{ type_id: "2", type_name: "连续剧" },
			{ type_id: "3", type_name: "综艺" },
			{ type_id: "4", type_name: "动漫" }
		],
		filters: {
			"1": [
				{ key: "type", name: "类型", value: [ {n:"全部",v:""}, {n:"喜剧",v:"喜剧"}, {n:"爱情",v:"爱情"}, {n:"恐怖",v:"恐怖"}, {n:"动作",v:"动作"}, {n:"科幻",v:"科幻"}, {n:"剧情",v:"剧情"}, {n:"战争",v:"战争"}, {n:"警匪",v:"警匪"}, {n:"犯罪",v:"犯罪"}, {n:"动画",v:"动画"}, {n:"奇幻",v:"奇幻"}, {n:"武侠",v:"武侠"}, {n:"冒险",v:"冒险"}, {n:"枪战",v:"枪战"}, {n:"悬疑",v:"悬疑"}, {n:"惊悚",v:"惊悚"}, {n:"经典",v:"经典"}, {n:"青春",v:"青春"}, {n:"文艺",v:"文艺"}, {n:"微电影",v:"微电影"}, {n:"古装",v:"古装"}, {n:"历史",v:"历史"}, {n:"运动",v:"运动"}, {n:"农村",v:"农村"}, {n:"儿童",v:"儿童"}, {n:"网络电影",v:"网络电影"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"大陆",v:"大陆"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"}, {n:"美国",v:"美国"}, {n:"法国",v:"法国"}, {n:"英国",v:"英国"}, {n:"日本",v:"日本"}, {n:"韩国",v:"韩国"}, {n:"德国",v:"德国"}, {n:"泰国",v:"泰国"}, {n:"印度",v:"印度"}, {n:"意大利",v:"意大利"}, {n:"西班牙",v:"西班牙"}, {n:"加拿大",v:"加拿大"}, {n:"其他",v:"其他"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}, {n:"2003",v:"2003"}, {n:"2002",v:"2002"}, {n:"2001",v:"2001"}, {n:"2000",v:"2000"} ] },
				{ key: "lang", name: "语言", value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"法语",v:"法语"}, {n:"德语",v:"德语"}, {n:"其它",v:"其它"} ] },
				{ key: "letter", name: "字母", value: [ {n:"全部",v:""}, {n:"A",v:"A"}, {n:"B",v:"B"}, {n:"C",v:"C"}, {n:"D",v:"D"}, {n:"E",v:"E"}, {n:"F",v:"F"}, {n:"G",v:"G"}, {n:"H",v:"H"}, {n:"I",v:"I"}, {n:"J",v:"J"}, {n:"K",v:"K"}, {n:"L",v:"L"}, {n:"M",v:"M"}, {n:"N",v:"N"}, {n:"O",v:"O"}, {n:"P",v:"P"}, {n:"Q",v:"Q"}, {n:"R",v:"R"}, {n:"S",v:"S"}, {n:"T",v:"T"}, {n:"U",v:"U"}, {n:"V",v:"V"}, {n:"W",v:"W"}, {n:"X",v:"X"}, {n:"Y",v:"Y"}, {n:"Z",v:"Z"}, {n:"0-9",v:"0-9"} ] },
				{ key: "sort", name: "按排序", value: [ {n:"最新",v:"time"}, {n:"最热",v:"hits"}, {n:"评分",v:"score"} ] }
			],
			"2": [
				{ key: "type", name: "类型", value: [ {n:"全部",v:""}, {n:"古装",v:"古装"}, {n:"战争",v:"战争"}, {n:"青春偶像",v:"青春偶像"}, {n:"喜剧",v:"喜剧"}, {n:"家庭",v:"家庭"}, {n:"犯罪",v:"犯罪"}, {n:"动作",v:"动作"}, {n:"奇幻",v:"奇幻"}, {n:"剧情",v:"剧情"}, {n:"历史",v:"历史"}, {n:"经典",v:"经典"}, {n:"乡村",v:"乡村"}, {n:"情景",v:"情景"}, {n:"商战",v:"商战"}, {n:"网剧",v:"网剧"}, {n:"其他",v:"其他"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"内地",v:"内地"}, {n:"韩国",v:"韩国"}, {n:"香港",v:"香港"}, {n:"台湾",v:"台湾"}, {n:"日本",v:"日本"}, {n:"美国",v:"美国"}, {n:"泰国",v:"泰国"}, {n:"英国",v:"英国"}, {n:"新加坡",v:"新加坡"}, {n:"其他",v:"其他"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}, {n:"2003",v:"2003"}, {n:"2002",v:"2002"}, {n:"2001",v:"2001"}, {n:"2000",v:"2000"} ] },
				{ key: "lang", name: "语言", value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"其它",v:"其它"} ] },
				{ key: "letter", name: "字母", value: [ {n:"全部",v:""}, {n:"A",v:"A"}, {n:"B",v:"B"}, {n:"C",v:"C"}, {n:"D",v:"D"}, {n:"E",v:"E"}, {n:"F",v:"F"}, {n:"G",v:"G"}, {n:"H",v:"H"}, {n:"I",v:"I"}, {n:"J",v:"J"}, {n:"K",v:"K"}, {n:"L",v:"L"}, {n:"M",v:"M"}, {n:"N",v:"N"}, {n:"O",v:"O"}, {n:"P",v:"P"}, {n:"Q",v:"Q"}, {n:"R",v:"R"}, {n:"S",v:"S"}, {n:"T",v:"T"}, {n:"U",v:"U"}, {n:"V",v:"V"}, {n:"W",v:"W"}, {n:"X",v:"X"}, {n:"Y",v:"Y"}, {n:"Z",v:"Z"}, {n:"0-9",v:"0-9"} ] },
				{ key: "sort", name: "按排序", value: [ {n:"最新",v:"time"}, {n:"最热",v:"hits"}, {n:"评分",v:"score"} ] }
			],
			"3": [
				{ key: "type", name: "类型", value: [ {n:"全部",v:""}, {n:"选秀",v:"选秀"}, {n:"情感",v:"情感"}, {n:"访谈",v:"访谈"}, {n:"播报",v:"播报"}, {n:"旅游",v:"旅游"}, {n:"音乐",v:"音乐"}, {n:"美食",v:"美食"}, {n:"纪实",v:"纪实"}, {n:"曲艺",v:"曲艺"}, {n:"生活",v:"生活"}, {n:"游戏互动",v:"游戏互动"}, {n:"财经",v:"财经"}, {n:"求职",v:"求职"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"内地",v:"内地"}, {n:"港台",v:"港台"}, {n:"日韩",v:"日韩"}, {n:"欧美",v:"欧美"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"} ] },
				{ key: "lang", name: "语言", value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"其它",v:"其它"} ] },
				{ key: "letter", name: "字母", value: [ {n:"全部",v:""}, {n:"A",v:"A"}, {n:"B",v:"B"}, {n:"C",v:"C"}, {n:"D",v:"D"}, {n:"E",v:"E"}, {n:"F",v:"F"}, {n:"G",v:"G"}, {n:"H",v:"H"}, {n:"I",v:"I"}, {n:"J",v:"J"}, {n:"K",v:"K"}, {n:"L",v:"L"}, {n:"M",v:"M"}, {n:"N",v:"N"}, {n:"O",v:"O"}, {n:"P",v:"P"}, {n:"Q",v:"Q"}, {n:"R",v:"R"}, {n:"S",v:"S"}, {n:"T",v:"T"}, {n:"U",v:"U"}, {n:"V",v:"V"}, {n:"W",v:"W"}, {n:"X",v:"X"}, {n:"Y",v:"Y"}, {n:"Z",v:"Z"}, {n:"0-9",v:"0-9"} ] },
				{ key: "sort", name: "按排序", value: [ {n:"最新",v:"time"}, {n:"最热",v:"hits"}, {n:"评分",v:"score"} ] }
			],
			"4": [
				{ key: "type", name: "类型", value: [ {n:"全部",v:""}, {n:"情感",v:"情感"}, {n:"科幻",v:"科幻"}, {n:"热血",v:"热血"}, {n:"推理",v:"推理"}, {n:"搞笑",v:"搞笑"}, {n:"冒险",v:"冒险"}, {n:"萝莉",v:"萝莉"}, {n:"校园",v:"校园"}, {n:"动作",v:"动作"}, {n:"机战",v:"机战"}, {n:"运动",v:"运动"}, {n:"战争",v:"战争"}, {n:"少年",v:"少年"}, {n:"少女",v:"少女"}, {n:"社会",v:"社会"}, {n:"原创",v:"原创"}, {n:"亲子",v:"亲子"}, {n:"益智",v:"益智"}, {n:"励志",v:"励志"}, {n:"其他",v:"其他"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"国产",v:"国产"}, {n:"日本",v:"日本"}, {n:"欧美",v:"欧美"}, {n:"其他",v:"其他"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}, {n:"2003",v:"2003"}, {n:"2002",v:"2002"}, {n:"2001",v:"2001"}, {n:"2000",v:"2000"} ] },
				{ key: "lang", name: "语言", value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"其它",v:"其它"} ] },
				{ key: "letter", name: "字母", value: [ {n:"全部",v:""}, {n:"A",v:"A"}, {n:"B",v:"B"}, {n:"C",v:"C"}, {n:"D",v:"D"}, {n:"E",v:"E"}, {n:"F",v:"F"}, {n:"G",v:"G"}, {n:"H",v:"H"}, {n:"I",v:"I"}, {n:"J",v:"J"}, {n:"K",v:"K"}, {n:"L",v:"L"}, {n:"M",v:"M"}, {n:"N",v:"N"}, {n:"O",v:"O"}, {n:"P",v:"P"}, {n:"Q",v:"Q"}, {n:"R",v:"R"}, {n:"S",v:"S"}, {n:"T",v:"T"}, {n:"U",v:"U"}, {n:"V",v:"V"}, {n:"W",v:"W"}, {n:"X",v:"X"}, {n:"Y",v:"Y"}, {n:"Z",v:"Z"}, {n:"0-9",v:"0-9"} ] },
				{ key: "sort", name: "按排序", value: [ {n:"最新",v:"time"}, {n:"最热",v:"hits"}, {n:"评分",v:"score"} ] }
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
    const type = extend.class || '';
    const sort = extend.sort || '';
    const letter = extend.letter || '';
    const lang = extend.lang || '';
	
	//https://www.aizju.com/vodshow/3-地区-排序-类型-语言-字母---分页---年份.html
    const res = Java.req(`${baseUrl}/vodshow/${tid}-${area}-${sort}-${type}-${lang}-${letter}---${pg}---${year}.html`);
    const doc = res.doc;
    const videos = parseVideoList(doc);
    
    let pages = [1, 1];
    let total = videos.length;
    try {
        const getPages = doc.querySelector("#conch-content .hl-page-total").textContent.replace(/\D*(\d+)\s*\/\s*(\d+)\D*/, '$1/$2');
        pages = getPages.split('/');
        total = doc.querySelector("#conch-content .hl-head-page em").textContent;
    } catch (e) {}
    return { code: 1, msg: "数据列表", list: videos, page: pages[0], pagecount: pages[1], limit: 36, total: pages[1] * 36 };
}

/**
 * 详情页
 */
async function detailContent(ids) {
    const res = Java.req(baseUrl + ids[0]);
    const doc = res.doc;

    const list = parseDetailPage(doc, ids[0]);
    return { code: 1, msg: "数据列表", page: 1, pagecount: 1, limit: 1, total: 1, list };
}


/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
	const url = `${baseUrl}/vodsearch/${key}----------${pg}---.html`;
	
	console.log("搜索被调用, 参数:", url, key, quick, pg);
	
    let res = Java.req(url);
	
    const vods = [];
    const items = res.doc.querySelectorAll('.hl-one-list .hl-list-item');
    
    items.forEach(item => {
        const link = item.querySelector('.hl-item-thumb');
        const vod = {
            vod_id: link?.getAttribute('href') || '',
            vod_name: link?.getAttribute('title') || '',
            vod_pic: link?.getAttribute('data-original') || '',

            vod_remarks: item.querySelector('.remarks')?.textContent?.trim() || '',
        };
        vods.push(vod);
    });
    
    const pageText = res.doc.querySelector('.hl-page-total')?.textContent || '1 / 1';
    const pages = pageText.split('/').map(num => parseInt(num.trim().replace('页', '')) || 1);
    
    return { code: 1, msg: "数据列表", list: vods, page: pages[0], pagecount: pages[1], limit: 12, total: pages[1] * 12 };
}

/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
    return { url: id, parse: 1 };
}


/* ---------------- 工具函数 ---------------- */

/**
 * 提取视频列表
 */
function parseVideoList(document) {
    const vods = [];
    const items = document.querySelectorAll('.hl-vod-list .hl-list-item');
    
    items.forEach(item => {
        const link = item.querySelector('.hl-item-thumb');
        const titleLink = item.querySelector('.hl-item-title a');
        
        const vod = {
            vod_id: link?.getAttribute('href') || titleLink?.getAttribute('href') || '',
            vod_name: link?.getAttribute('title') || titleLink?.getAttribute('title') || '',
            vod_pic: link?.getAttribute('data-original') || '',
            vod_remarks: item.querySelector('.remarks')?.textContent?.trim() || '',
        };
        
        vods.push(vod);
    });
    
    return vods;
}

/**
 * 解析详情页
 */
function parseDetailPage(document, vod_id) {

    const vod_name = document.querySelector('.video-name')?.textContent?.trim() || '';
    const vod_pic = document.querySelector('.hl-item-thumb')?.getAttribute('data-original') || '';
    const vod_year = document.querySelector('.video-class')?.firstChild?.textContent?.trim() || '';
    const vod_content = document.querySelector('li.hl-col-xs-12[style*="font-size: 14px"]')?.textContent?.replace('简介', '').trim() || '';
    
    const playSources = document.querySelectorAll('.hl-playlists');
    const vod_play_from = Array.from(playSources).map(item => item.getAttribute('alt')).filter(Boolean).join('$$$');
    
    const playBoxes = document.querySelectorAll('.hl-tabs-box');
    const playUrls = [];
    playBoxes.forEach(box => {
        const episodes = Array.from(box.querySelectorAll('a[href*="/vodplay/"]')).map(link => {
            const epName = link.textContent?.trim();
            const epUrl = link.getAttribute('href');
            const fullUrl = epUrl.startsWith('http') ? epUrl : baseUrl + epUrl;
            return `${epName}$${fullUrl}`;
        }).filter(ep => ep);
        if (episodes.length > 0) {
            playUrls.push(episodes.join('#'));
        }
    });
    const vod_play_url = playUrls.join('$$$');
    
    return [{
        vod_id: vod_id,
        vod_name: vod_name,
        vod_pic: vod_pic,
        vod_remarks: '',
        vod_year: vod_year,
        vod_lang: '国语',
        vod_content: vod_content,
        vod_play_from: vod_play_from,
        vod_play_url: vod_play_url
    }];
}
