/**
 * 飞快TV 爬虫
 * 版本：3.0 - WvSpider v2.0 新架构
 * 最后更新：2025-12-23
 * 发布页 https://feikuai.tv/
 */

const baseUrl = 'https://feikuai.tv/';

/**
 * 初始化方法
 */
function init(cfg) {
    return {
        webview: {
            debug: true,
            showWebView: true,
            widthPercent: 80,
			keywords:'系统安全验证|系统提示......|人机验证',
            heightPercent: 60,
            timeout: 30,
            header: { 'Referer': baseUrl },
            blockList: [
                "*.css*",
                "*.ico*",
                "*.png*",
                "*.jpg*",
                "*.jpeg*",
                "*.gif*",
                "*.webp*",
                "https://bossjs.rosfky.cn/gg-config.js",
                "*.mq5yjm.com*",
                "*:8005*"
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
			{ type_id: "dianying", type_name: "电影" },
			{ type_id: "juji", type_name: "剧集" },
			{ type_id: "dongman", type_name: "动漫" },
			{ type_id: "zongyi", type_name: "综艺" },
			{ type_id: "duanju", type_name: "短剧" }
		],
		filters: {
			"dianying": [
				{ key: "type", name: "类型", value: [ {n:"全部",v:""}, {n:"动作片",v:"dongzuopian"}, {n:"喜剧片",v:"xijupian"}, {n:"爱情片",v:"aiqingpian"}, {n:"科幻片",v:"kehuanpian"}, {n:"恐怖片",v:"kongbupian"}, {n:"剧情片",v:"juqingpian"}, {n:"战争片",v:"zhanzhengpian"}, {n:"动画片",v:"donghuapian"} ] },
				{ key: "cate", name: "剧情", value: [ {n:"全部",v:""}, {n:"Netflix",v:"Netflix"}, {n:"喜剧",v:"喜剧"}, {n:"爱情",v:"爱情"}, {n:"恐怖",v:"恐怖"}, {n:"动作",v:"动作"}, {n:"科幻",v:"科幻"}, {n:"剧情",v:"剧情"}, {n:"战争",v:"战争"}, {n:"犯罪",v:"犯罪"}, {n:"动画",v:"动画"}, {n:"奇幻",v:"奇幻"}, {n:"武侠",v:"武侠"}, {n:"冒险",v:"冒险"}, {n:"枪战",v:"枪战"}, {n:"悬疑",v:"悬疑"}, {n:"惊悚",v:"惊悚"}, {n:"古装",v:"古装"}, {n:"历史",v:"历史"}, {n:"家庭",v:"家庭"}, {n:"同性",v:"同性"}, {n:"运动",v:"运动"}, {n:"儿童",v:"儿童"}, {n:"经典",v:"经典"}, {n:"青春",v:"青春"}, {n:"文艺",v:"文艺"}, {n:"微电影",v:"微电影"}, {n:"纪录片",v:"纪录片"}, {n:"网络电影",v:"网络电影"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"中国大陆",v:"中国大陆"}, {n:"美国",v:"美国"}, {n:"韩国",v:"韩国"}, {n:"日本",v:"日本"}, {n:"泰国",v:"泰国"}, {n:"中国香港",v:"中国香港"}, {n:"中国台湾",v:"中国台湾"}, {n:"新加坡",v:"新加坡"}, {n:"马来西亚",v:"马来西亚"}, {n:"印度",v:"印度"}, {n:"英国",v:"英国"}, {n:"法国",v:"法国"}, {n:"德国",v:"德国"}, {n:"加拿大",v:"加拿大"}, {n:"西班牙",v:"西班牙"}, {n:"俄罗斯",v:"俄罗斯"}, {n:"其它",v:"其它"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}, {n:"2003",v:"2003"}, {n:"2002",v:"2002"}, {n:"2001",v:"2001"}, {n:"2000",v:"2000"}, {n:"1999",v:"1999"}, {n:"1998",v:"1998"}, {n:"1997",v:"1997"}, {n:"1996",v:"1996"}, {n:"1995",v:"1995"}, {n:"1994",v:"1994"}, {n:"1993",v:"1993"}, {n:"1992",v:"1992"}, {n:"1991",v:"1991"}, {n:"1990",v:"1990"}, {n:"1989",v:"1989"}, {n:"1988",v:"1988"}, {n:"1987",v:"1987"}, {n:"1986",v:"1986"}, {n:"1985",v:"1985"}, {n:"1984",v:"1984"}, {n:"1983",v:"1983"}, {n:"1982",v:"1982"}, {n:"1981",v:"1981"}, {n:"1980",v:"1980"} ] },
				{ key: "sort", name: "排序", value: [ {n:"时间排序",v:"time"}, {n:"人气排序",v:"hits"}, {n:"评分排序",v:"score"} ] }
			],
			"juji": [
				{ key: "type", name: "类型", value: [ {n:"全部",v:""}, {n:"国产剧",v:"guochanju"}, {n:"港台剧",v:"gangtaiju"}, {n:"日韩剧",v:"rihanju"}, {n:"欧美剧",v:"oumeiju"}, {n:"泰国剧",v:"taiguoju"} ] },
				{ key: "cate", name: "剧情", value: [ {n:"全部",v:""}, {n:"Netflix",v:"Netflix"}, {n:"爱情",v:"爱情"}, {n:"言情",v:"言情"}, {n:"都市",v:"都市"}, {n:"家庭",v:"家庭"}, {n:"战争",v:"战争"}, {n:"喜剧",v:"喜剧"}, {n:"古装",v:"古装"}, {n:"武侠",v:"武侠"}, {n:"偶像",v:"偶像"}, {n:"历史",v:"历史"}, {n:"悬疑",v:"悬疑"}, {n:"科幻",v:"科幻"}, {n:"冒险",v:"冒险"}, {n:"惊悚",v:"惊悚"}, {n:"犯罪",v:"犯罪"}, {n:"运动",v:"运动"}, {n:"恐怖",v:"恐怖"}, {n:"剧情",v:"剧情"}, {n:"奇幻",v:"奇幻"}, {n:"纪录片",v:"纪录片"}, {n:"灾难",v:"灾难"}, {n:"动作",v:"动作"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"中国大陆",v:"中国大陆"}, {n:"美国",v:"美国"}, {n:"韩国",v:"韩国"}, {n:"日本",v:"日本"}, {n:"泰国",v:"泰国"}, {n:"中国香港",v:"中国香港"}, {n:"中国台湾",v:"中国台湾"}, {n:"新加坡",v:"新加坡"}, {n:"马来西亚",v:"马来西亚"}, {n:"印度",v:"印度"}, {n:"英国",v:"英国"}, {n:"法国",v:"法国"}, {n:"德国",v:"德国"}, {n:"加拿大",v:"加拿大"}, {n:"西班牙",v:"西班牙"}, {n:"俄罗斯",v:"俄罗斯"}, {n:"其它",v:"其它"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}, {n:"2003",v:"2003"}, {n:"2002",v:"2002"}, {n:"2001",v:"2001"}, {n:"2000",v:"2000"}, {n:"1999",v:"1999"}, {n:"1998",v:"1998"}, {n:"1997",v:"1997"}, {n:"1996",v:"1996"}, {n:"1995",v:"1995"}, {n:"1994",v:"1994"}, {n:"1993",v:"1993"}, {n:"1992",v:"1992"}, {n:"1991",v:"1991"}, {n:"1990",v:"1990"}, {n:"1989",v:"1989"}, {n:"1988",v:"1988"}, {n:"1987",v:"1987"}, {n:"1986",v:"1986"}, {n:"1985",v:"1985"}, {n:"1984",v:"1984"}, {n:"1983",v:"1983"}, {n:"1982",v:"1982"}, {n:"1981",v:"1981"}, {n:"1980",v:"1980"} ] },
				{ key: "sort", name: "排序", value: [ {n:"时间排序",v:"time"}, {n:"人气排序",v:"hits"}, {n:"评分排序",v:"score"} ] }
			],
			"zongyi": [
				{ key: "cate", name: "剧情", value: [ {n:"全部",v:""}, {n:"Netflix",v:"Netflix"}, {n:"纪录片",v:"纪录片"}, {n:"真人秀",v:"真人秀"}, {n:"音乐",v:"音乐"}, {n:"喜剧",v:"喜剧"}, {n:"脱口秀",v:"脱口秀"}, {n:"文化",v:"文化"}, {n:"美食",v:"美食"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"中国大陆",v:"中国大陆"}, {n:"美国",v:"美国"}, {n:"韩国",v:"韩国"}, {n:"日本",v:"日本"}, {n:"中国香港",v:"中国香港"}, {n:"中国台湾",v:"中国台湾"}, {n:"印度",v:"印度"}, {n:"英国",v:"英国"}, {n:"法国",v:"法国"}, {n:"德国",v:"德国"}, {n:"加拿大",v:"加拿大"}, {n:"西班牙",v:"西班牙"}, {n:"俄罗斯",v:"俄罗斯"}, {n:"其它",v:"其它"} ] },
				{ key: "lang", name: "语言", value: [ {n:"全部",v:""}, {n:"国语",v:"国语"}, {n:"英语",v:"英语"}, {n:"粤语",v:"粤语"}, {n:"闽南语",v:"闽南语"}, {n:"韩语",v:"韩语"}, {n:"日语",v:"日语"}, {n:"其它",v:"其它"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}, {n:"2003",v:"2003"}, {n:"2002",v:"2002"}, {n:"2001",v:"2001"}, {n:"2000",v:"2000"}, {n:"1990",v:"1990"}, {n:"1980",v:"1980"}, {n:"1970",v:"1970"}, {n:"1960",v:"1960"}, {n:"1950",v:"1950"} ] },
				{ key: "sort", name: "排序", value: [ {n:"时间排序",v:"time"}, {n:"人气排序",v:"hits"}, {n:"评分排序",v:"score"} ] }
			],
			"dongman": [
				{ key: "cate", name: "剧情", value: [ {n:"全部",v:""}, {n:"奇幻",v:"奇幻"}, {n:"动作",v:"动作"}, {n:"科幻",v:"科幻"}, {n:"喜剧",v:"喜剧"}, {n:"冒险",v:"冒险"}, {n:"后宫",v:"后宫"}, {n:"爱情",v:"爱情"}, {n:"悬疑",v:"悬疑"}, {n:"机战",v:"机战"}, {n:"战争",v:"战争"}, {n:"其他",v:"其他"} ] },
				{ key: "area", name: "地区", value: [ {n:"全部",v:""}, {n:"中国大陆",v:"中国大陆"}, {n:"日本",v:"日本"}, {n:"美国",v:"美国"}, {n:"韩国",v:"韩国"}, {n:"中国香港",v:"中国香港"}, {n:"中国台湾",v:"中国台湾"}, {n:"英国",v:"英国"}, {n:"法国",v:"法国"}, {n:"加拿大",v:"加拿大"}, {n:"西班牙",v:"西班牙"}, {n:"俄罗斯",v:"俄罗斯"}, {n:"其它",v:"其它"} ] },
				{ key: "year", name: "年份", value: [ {n:"全部",v:""}, {n:"2026",v:"2026"}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"2019",v:"2019"}, {n:"2018",v:"2018"}, {n:"2017",v:"2017"}, {n:"2016",v:"2016"}, {n:"2015",v:"2015"}, {n:"2014",v:"2014"}, {n:"2013",v:"2013"}, {n:"2012",v:"2012"}, {n:"2011",v:"2011"}, {n:"2010",v:"2010"}, {n:"2009",v:"2009"}, {n:"2008",v:"2008"}, {n:"2007",v:"2007"}, {n:"2006",v:"2006"}, {n:"2005",v:"2005"}, {n:"2004",v:"2004"}, {n:"2003",v:"2003"}, {n:"2002",v:"2002"}, {n:"2001",v:"2001"}, {n:"2000",v:"2000"}, {n:"1999",v:"1999"}, {n:"1998",v:"1998"}, {n:"1997",v:"1997"}, {n:"1996",v:"1996"}, {n:"1995",v:"1995"}, {n:"1994",v:"1994"}, {n:"1993",v:"1993"}, {n:"1992",v:"1992"}, {n:"1991",v:"1991"}, {n:"1990",v:"1990"}, {n:"1989",v:"1989"}, {n:"1988",v:"1988"}, {n:"1987",v:"1987"}, {n:"1986",v:"1986"}, {n:"1985",v:"1985"}, {n:"1984",v:"1984"}, {n:"1983",v:"1983"}, {n:"1982",v:"1982"}, {n:"1981",v:"1981"}, {n:"1980",v:"1980"} ] },
				{ key: "sort", name: "排序", value: [ {n:"时间排序",v:"time"}, {n:"人气排序",v:"hits"}, {n:"评分排序",v:"score"} ] }
			],
			"duanju": [
				{ key: "cate", name: "剧情", value: [ {n:"全部",v:""}, {n:"都市",v:"都市"}, {n:"古装",v:"古装"}, {n:"穿越",v:"穿越"}, {n:"重生",v:"重生"}, {n:"逆袭",v:"逆袭"}, {n:"赘婿",v:"赘婿"}, {n:"战神",v:"战神"}, {n:"神医",v:"神医"}, {n:"甜宠",v:"甜宠"}, {n:"虐恋",v:"虐恋"}, {n:"言情",v:"言情"} ] },
				{ key: "sort", name: "排序", value: [ {n:"时间排序",v:"time"}, {n:"人气排序",v:"hits"}, {n:"评分排序",v:"score"} ] }
			]
		}
	};
    return filterConfig;
}

/**
 * 首页推荐视频
 */
async function homeVideoContent() {
    const document = await Java.wvOpen(baseUrl);
    return { list: parseVideoList() };
}

/**
 * 分类列表
 */
async function categoryContent(tid, pg, filter, extend) {
    console.log(`分类: tid=${tid}, pg=${pg}`);
	const document = await Java.wvOpen(`${baseUrl}/vodshow[/area/${extend?.area}][/by/${extend?.sort}][/class/${extend?.cate}]/id/${extend?.type||tid}[/year/${extend?.year}]/page/${pg||1}.html`);
	
    const pagecount = parseInt($('#page a[title="尾页"]')?.href?.match(/page\/(\d+)/)?.[1] || '1');
    return { 
        code: 1, 
        msg: "数据列表", 
        list: parseVideoList(), 
        page: parseInt(pg) || 1, 
        pagecount: pagecount, 
        limit: 40, 
        total: pagecount * 40
    };
}

/**
 * 详情页
 */
async function detailContent(ids) {
	console.log('获取到的id', ids);
	
	const document = await Java.wvOpen(ids[0]);
	
    return {
        code: 1,
        msg: "数据列表",
        list: parseDetailPage(), 
        page: 1, 
        pagecount: 1,
        limit: 1, 
        total: 1
    };
}

/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
	console.log("搜索翻页", pg)
	// let result = Java.showCaptchaEx({
		// title: '安全验证',
		// message: '请输入下方图片中的验证码',
		// imageUrl: 'https://www.jqqzx.top/index.php/verify/index.html?',
		// headers: { Cookie: 'PHPSESSID=1d91plvokud90usu538h01778i' }
	// });
	// if (result.confirmed) {
		// Java.showAlert('取到的验证吗', result.input);
	// }
    // const url = `${baseUrl}/vodsearch${encodeURIComponent(key)}/page/${pg||1}.html`;
    // const res = await Java.req(url);
    
    // 解析视频列表
    // const vods = [...res.doc.querySelectorAll('.module-card-item')].map(item => ({
        // vod_id: baseUrl + item.querySelector('a.module-card-item-poster').getAttribute('href'),
        // vod_name: item.querySelector('.module-card-item-title strong').textContent.trim(),
        // vod_pic: item.querySelector('img').getAttribute('data-original'),
        // vod_remarks: item.querySelector('.module-item-note')?.textContent.trim() || ''
    // }));
    
    // 提取总页数和总数量
    // const pagecount = parseInt(res.doc.querySelector('#page a[title="尾页"]')?.getAttribute('href')?.match(/page\/(\d+)/)?.[1] || '1');
    // const total = parseInt(res.doc.querySelector('.mac_total')?.textContent || '0');
    const vods = [];
    let pageSize = 2; // 每页显示数量
	// if(pg >= 2) pageSize= 20;
    const totalPages = 20; // 总页数
    const totalItems = pageSize * totalPages; // 总数据量
    
    // 计算当前页的起始序号
    const startIndex = (pg - 1) * pageSize + 1;
    
    for (let i = 0; i < pageSize; i++) {
        const currentNum = startIndex + i;
        vods.push({
            vod_id: currentNum === 1 ? 'searchKeyWord' : `searchKeyWord_${currentNum}`,
            vod_name: currentNum === 1 ? '点击输入验证码' : `searchKeyWord_${currentNum}`,
            vod_remarks: `备注_${currentNum}`,
            vod_year: `年份_${currentNum}`,
            vod_director: `导演_${currentNum}`
        });
    }
    
    return {
        code: 1,
        msg: "数据列表",
        list: vods,
        page: pg,
        pagecount: totalPages,
        limit: pageSize,
        total: totalItems
    };
}

/**
 * 播放器
 * 
 * parse 参数说明：
 * - 0: 直接播放 url
 * - 1: 需要解析的 url
 * - 2: 使用自定义嗅探（wvSpider内部嗅探）
 */
async function playerContent(flag, id, vipFlags) {
    console.log("播放内容:", flag, id);
    return {
        type: 'sniff',
        url: id,
        keyword: '.m3u8|.mp4',
        script: `let t=setInterval(()=>{let s=document.querySelector('iframe[src*="player.php"]')?.contentDocument?.querySelector('#start');if(s){s.click();clearInterval(t)}},100);`,
        timeout: 15
    };
}

async function action(action) {
    console.log("收到的动作:", action);
}


/* ---------------- 工具函数 ---------------- */

/**
 * 提取视频列表
 */
function parseVideoList() {
    const vods = [];
    document.querySelectorAll('a.module-poster-item').forEach(item => {
        vods.push({
            vod_id: baseUrl + (item.getAttribute('href') || ''),
            vod_name: item.getAttribute('title') || '',
            vod_pic: item.querySelector('img')?.getAttribute('data-original') || '',
            vod_remarks: item.querySelector('.module-item-note')?.textContent?.trim() || ''
        });
    });
    return vods;
}

/**
 * 解析详情页
 */
function parseDetailPage() {
    // 辅助函数
    const text = s => document.querySelector(s)?.textContent?.trim() || '';
    const attr = (s, a) => document.querySelector(s)?.getAttribute(a) || '';
    const findInfo = label => [...document.querySelectorAll('.module-info-item')].find(el => el.textContent.includes(label));
    
    // 解析播放列表
    const playUrls = [];
    document.querySelectorAll('.his-tab-list').forEach(list => {  // 修正：使用 querySelectorAll
        const eps = [...list.querySelectorAll('.module-play-list-link')].map(link => {
            const name = link.querySelector('span')?.textContent?.trim();
            const url = baseUrl + link.getAttribute('href');
            return name && url ? `${name}$${url}` : null;
        }).filter(Boolean);
        if (eps.length) playUrls.push(eps.join('#'));
    });
    
    // 获取线路名称
    const playFrom = [...document.querySelectorAll('.module-tab-item span')]
        .map(s => s.textContent.trim())
        .filter(Boolean)
        .join('$$$');
    
    return [{
        vod_id: location.href,
        vod_name: text('.module-info-heading h1'),
        vod_pic: attr('.module-item-pic img', 'data-original'),
        vod_remarks: findInfo('集数')?.querySelector('.module-info-item-content')?.textContent?.trim() || '',
        vod_year: attr('.module-info-tag-link a[title*="202"]', 'title'),
        vod_director: findInfo('导演') 
            ? [...findInfo('导演').querySelectorAll('a')].map(a => a.textContent.trim()).join('/') 
            : '',
        vod_actor: findInfo('主演') 
            ? [...findInfo('主演').querySelectorAll('a')].map(a => a.textContent.trim()).join('/') 
            : '',
        vod_content: text('.module-info-introduction-content p'),
        vod_play_from: playFrom,
        vod_play_url: playUrls.join('$$$')
    }];
}

/* ---------------- 导出对象 ---------------- */
const spider = { init, homeContent, homeVideoContent, categoryContent, detailContent, searchContent, playerContent, action };
spider;
