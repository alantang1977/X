/**
 * 新韩剧网(hanju7.com)爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-19
 * 发布页 https://www.hanju7.com/
 *
 * @config
 * debug: true
 // * showWebView: true
 * percent: 80,60
 * returnType: dom
 * timeout: 30
 * blockImages: true
 * blockList: *.[ico|png|jpeg|jpg|gif|webp]*,.css
 */
 
const baseUrl = 'https://www.hanju7.com';

/**
 * 初始化配置
 */
async function init(cfg) {
	
    return;
}

/**
 * 首页分类
 */
async function homeContent(filter) {
	const filterConfig = {
		class: [
			{ type_id: "1", type_name: "韩剧" },
			{ type_id: "3", type_name: "韩国电影" },
			{ type_id: "4", type_name: "韩国综艺" },
			{ type_id: "hot", type_name: "排行榜" },
			{ type_id: "new", type_name: "最新更新" }
		],
		filters: {
			"1": [
				{ key: "year",  name: "按年份",  value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"10后",v:"2010__2019"}, {n:"00后",v:"2000__2009"}, {n:"90后",v:"1990__1999"}, {n:"80后",v:"1980__1989"}, {n:"更早",v:"1900__1980"} ] },
				{ key: "sort",  name: "按排序",  value: [ {n:"最新",v:"newstime"}, {n:"热门",v:"onclick"} ] }
			],
			"3": [
				{ key: "year",  name: "按年份",  value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"10后",v:"2010__2019"}, {n:"00后",v:"2000__2009"}, {n:"90后",v:"1990__1999"}, {n:"80后",v:"1980__1989"}, {n:"更早",v:"1900__1980"} ] },
				{ key: "sort",  name: "按排序",  value: [ {n:"最新",v:"newstime"}, {n:"热门",v:"onclick"} ] }
			],
			"4": [
				{ key: "year",  name: "按年份",  value: [ {n:"全部",v:""}, {n:"2025",v:"2025"}, {n:"2024",v:"2024"}, {n:"2023",v:"2023"}, {n:"2022",v:"2022"}, {n:"2021",v:"2021"}, {n:"2020",v:"2020"}, {n:"10后",v:"2010__2019"}, {n:"00后",v:"2000__2009"}, {n:"90后",v:"1990__1999"}, {n:"80后",v:"1980__1989"}, {n:"更早",v:"1900__1980"} ] },
				{ key: "sort",  name: "按排序",  value: [ {n:"最新",v:"newstime"}, {n:"热门",v:"onclick"} ] }
			]
		}
	};


    return filterConfig;
}

/**
 * 首页推荐视频
 */
async function homeVideoContent() {
    const document = await Java.wvOpen(`${baseUrl}/`);  // 使用模板字符串
    const videos = parseVideoList(document);
    return { list: videos };
}

/**
 * 分类内容
 */
async function categoryContent(tid, pg, filter, extend) {
    // console.log("筛选参数:", extend, `type=${type}, area=${area}, year=${year}, cat=${cat}, sort=${sort}, lang=${lang}`);
    const year = extend.year || '';
    const sort = extend.sort || '';
	Java.wvOpen(`${baseUrl}/list/${tid}-${year}-${sort}-${pg}.html`).when('tid=hot|new', `${baseUrl}/${tid}.html`);

    if (tid === 'hot' || tid === 'new') {
        // 排行榜或最新更新
        // const document = await Java.req(`${baseUrl}/${tid}.html`);
        let i = 1;
        const videos = Array.from(document.querySelectorAll('#t ~ li')).map(li => ({
            vod_id: baseUrl + li.querySelector('a[href^="/detail/"]').getAttribute('href'),
            vod_name: li.querySelector('a').textContent,
            vod_year: li.querySelector('#time').textContent,
            vod_pic: 'https://dummyimage.com/240x240/ffffff/ffc800.png&text=' + (i++), // 搞个占位图
            vod_remarks: li.querySelector('#time').textContent + ' | ' + li.querySelector('#actor').textContent,
            style: {
                type : 'list'
            }
        }));

        // console.log("视频列表:", { code: 1, msg: "数据列表", list: videos, page: 1, pagecount: 1, limit: 100, total: 100 } );

        return { code: 1, msg: "数据列表", list: videos, page: 1, pagecount: 1, limit: 100, total: 100 };
    } else {
        // 普通分类
        // https://www.hanju7.com/list/1-2024-onclick-1.html
        // const document = await Java.wvOpen(`${baseUrl}/list/${tid}-${year}-${sort}-${pg}.html`);
        const videos = parseVideoList(document);
        return { code: 1, msg: "数据列表", list: videos, page: pg, pagecount: 10000, limit: 24, total: 240000 };
    }
}

/**
 * 详情页
 */
async function detailContent(ids) {
    const document = await Java.wvOpen(ids[0]);
    const getText = (dtText) => {
        const dt = Array.from(document.querySelectorAll('dt')).find(el => el.textContent.includes(dtText));
        return dt ? dt.nextElementSibling.textContent.trim() : '';
    };

    const playItems = Array.from(document.querySelectorAll('.play a[onclick]')).map(a => {
        const match = a.getAttribute('onclick').match(/bb_a\('([^']+)','([^']+)'/);
        return `${match[2]}$${match[1]}`;
    });

    list = [{
        vod_id: ids[0],
        vod_name: getText('片名'),
        vod_pic: 'https:' + document.querySelector('img[src*="//pics.hanju7.com/"]').getAttribute('src'),
        vod_remarks: getText('状态'),
        vod_year: getText('上映').split('-')[0],
        vod_actor: getText('主演'),
        vod_content: document.querySelector(".juqing").textContent.replace(/\s+/g, ' ').trim(),
        vod_play_from: '新韩剧网',
        vod_play_url: playItems.join('#')
    }];

    console.log("详情列表:", list);
    return { code: 1, msg: "数据列表", page: 1, pagecount: 1, limit: 1, total: 1, list };
}

/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
    let res = await Java.req(`${baseUrl}/search/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `show=searchkey&keyboard=${encodeURIComponent(key)}`
    });
    // console.log("搜索响应:", res);

    const document = res.doc;
    const videos = Array.from(document.querySelectorAll('#t ~ li')).map(li => ({
        vod_id: baseUrl + li.querySelector('a[href^="/detail/"]').getAttribute('href'),
        vod_name: li.querySelector('a').getAttribute('title'),
        vod_year: li.querySelector('#time').textContent,
        vod_remarks: li.querySelector('a').textContent.match(/\((\d{4})\)/)?.[1] + ' | ' + li.querySelector('#actor').textContent,

    }));
    const total = videos.length;
    return { code: 1, msg: "数据列表", list: videos, page: 1, pagecount: 1, limit: total, total: total };
}

/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
    // Java.showWebView();

    const ids = id.split('_');
    const playPageUrl = `https://www.hanju7.com/detail/${ids[0]}.html`;
    return {
        type: 'sniff',
        url: playPageUrl,
        keyword: '.m3u8|.mp4',
        script: `document.querySelectorAll('.play a[onclick]')[${ids[2] - 1}]?.click();`,
        timeout: 15
    };
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
    const list = Array.from(document.querySelectorAll('.list li')).map(li => ({
        vod_id: baseUrl + li.querySelector('a[href^="/detail/"]').getAttribute('href'),
        vod_name: li.querySelector('a[href^="/detail/"]').getAttribute('title'),
        vod_pic: 'https:' + li.querySelector('a').getAttribute('data-original'),
        vod_year: li.querySelector('.tip').textContent
    }));
    return list;
}


/**
 * 解析详情页
 */
function parseDetailPage(document) {
}


/* ---------------- 导出对象 ---------------- */
const spider = { init, homeContent, homeVideoContent, categoryContent, detailContent, searchContent, playerContent, action };
spider;
