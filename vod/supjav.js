/**
 * SupJav 爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-17
 * 发布页 https://supjav.com/zh
 */

const baseUrl = 'https://supjav.com/zh';

/**
 * 初始化配置
 */
async function init(cfg) {
    return {
        webview: {
            debug: true,              // 是否开启调试模式
            showWebView: false,       // 默认不显示
            widthPercent: 80,        // 窗口宽度百分比
            heightPercent: 40,       // 窗口高度百分比
            keyword: '',              // 页面不存在该关键字时显示webview
            returnType: 'dom',        // 返回DOM对象
            timeout: 30,              // 超时时间（秒）
            blockImages: false,       // 是否禁止加载图片
            enableJavaScript: true,   // 是否启用JS
            header: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Referer': baseUrl + '/',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
        }
    };
}

/**
 * 首页分类
 */
async function homeContent(filter) {
    return {
        class: [
            { type_id: "popular", type_name: "热门" },
            { type_id: "category/censored-jav", type_name: "有码" },
            { type_id: "category/uncensored-jav", type_name: "无码" },
            { type_id: "category/amateur", type_name: "素人" },
            { type_id: "category/chinese-subtitles", type_name: "中文字幕" },
            { type_id: "category/english-subtitles", type_name: "英文字幕" },
            { type_id: "category/reducing-mosaic", type_name: "无码破解" }
        ]
    };
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
    const pgSuffix = (pg === 1 ? '' : `/page/${pg}`);
    const document = await Java.wvOpen(`${baseUrl}/${tid}${pgSuffix}`);
    const videos = parseVideoList(document);
    return { code: 1, msg: "数据列表", list: videos, page: pg, pagecount: 10000, limit: 24, total: 240000 };
}

/**
 * 详情页
 */
async function detailContent(ids) {
    const document = await Java.wvOpen(ids[0]);
    const list = parseDetailPage(document, ids[0]);
    return list;
}

/**
 * 搜索
 */
async function searchContent(key, quick, pg) {
    // 暂未实现搜索逻辑
    return { list: [] };
}

/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
    const ids = id.split('---');
    Java.showWebView();

	return {
		type: 'sniff',           // 必填，标识嗅探模式
		url: ids[1],             // 必填，要加载的播放页面 URL
		keyword: '.m3u8|.mp4',   // 可选，嗅探关键字，多个用 | 分隔
		script: `
        (function(){
            setTimeout(() => {
                document.querySelectorAll('.btn-server').forEach(btn => {
                    if(btn.textContent.trim() === '${ids[0]}') {
                        btn.click();
                        console.log('已点击服务器: ${ids[0]}');
                    }
                });
                setTimeout(() => {
                    document.querySelector("#a > div.spin").click();
                    console.log('已点击播放按钮');
                }, 3000);
            }, 500);
        })();
    `,
		timeout: 15              // 可选，嗅探超时时间（秒），默认 15
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
    return { list: [] };
}


/* ---------------- 工具函数 ---------------- */

/**
 * 提取视频列表
 */
function parseVideoList(document) {
    const posts = document.querySelectorAll('.post');
    return Array.from(posts).map(post => {
        const titleLink = post.querySelector('h3 a');
        const vod_name = titleLink?.getAttribute('title') || titleLink?.textContent || '';
        const vod_id = titleLink?.getAttribute('href') || '';
        const img = post.querySelector('img');
        const vod_pic = img?.getAttribute('data-original') || img?.getAttribute('src') || '';
        const meta = post.querySelector('.meta');
        let vod_remarks = '';
        if (meta) {
            const metaText = meta.textContent || '';
            const viewsMatch = metaText.match(/(\d+)\s*Views/);
            if (viewsMatch) {
                vod_remarks = `${viewsMatch[1]}次浏览`;
            } else {
                const chineseMatch = metaText.match(/(\d+)\s*次浏览/);
                vod_remarks = chineseMatch ? `${chineseMatch[1]}次浏览` : '';
            }
        }
        return { vod_id, vod_name, vod_pic, vod_remarks };
    });
}

/**
 * 解析详情页
 */
function parseDetailPage(doc, id) {
    const title = doc.querySelector('.archive-title h1')?.textContent?.trim() || '';
    const vod_pic = doc.querySelector('.post-meta .img')?.src || '';
    const viewsText = doc.querySelector('.dz_view .views')?.textContent || '';
    const vod_remarks = viewsText.replace(/[^0-9]/g, '') || '0';
    const tagElements = doc.querySelectorAll('.tags a');
    const vod_actor = Array.from(tagElements).map(tag => tag.textContent.trim()).join(',');
    let vod_director = '';
    const catElements = doc.querySelectorAll('.cats p, .cats span, .cats a');
    for (let el of catElements) {
        if (el.textContent.includes('Maker')) {
            if (el.nextElementSibling?.tagName === 'A') {
                vod_director = el.nextElementSibling.textContent.trim();
                break;
            }
            const linkInParent = el.querySelector('a');
            if (linkInParent) {
                vod_director = linkInParent.textContent.trim();
                break;
            }
        }
    }
    const vod_content = doc.querySelector('.post-content')?.textContent?.trim() || '';
    const serverButtons = doc.querySelectorAll('.btnst .btn-server');
    const playItems = Array.from(serverButtons).map(btn => {
        const serverName = btn.textContent.trim();
        const dataLink = btn.getAttribute('data-link');
        return serverName && dataLink ? `${serverName}$${serverName}---${id}` : '';
    }).filter(Boolean);
    const vod_play_url = playItems.join('#') || '';
    const vod = {
        code: 1,
        msg: "数据列表",
        page: 1,
        pagecount: 1,
        limit: 1,
        total: 1,
        list: [{
            vod_id: id || 'unknown_id',
            vod_name: title,
            vod_pic: vod_pic,
            vod_remarks: vod_remarks,
            vod_director: vod_director,
            vod_actor: vod_actor,
            vod_content: vod_content,
            vod_play_from: 'SERVER',
            vod_play_url: vod_play_url
        }]
    };
	// console.log(vod);
	return vod;
}


/* ---------------- 导出对象 ---------------- */
const spider = { init, homeContent, homeVideoContent, categoryContent, detailContent, searchContent, playerContent, action };
spider;
