/**
 * 天天影院爬虫 - 优化正则匹配
 */

const baseUrl = 'https://www.baixiaotangtop.com';

function homeContent() {
    return {
        class: [
            { type_id: "1", type_name: "电影" },
            { type_id: "2", type_name: "电视剧" },
            { type_id: "3", type_name: "综艺" },
            { type_id: "4", type_name: "动漫" },
            { type_id: "36", type_name: "短剧" }
        ],
        filters: {}
    };
}

async function homeVideoContent() {
    let resp = await Java.req(baseUrl);
    let list = parseHtmlForList(resp.body);
    return { list: list };
}

async function categoryContent(tid, pg) {
    let url = baseUrl + '/vodshow/' + tid + '--------' + pg + '---.html';
    let resp = await Java.req(url);
    let list = parseHtmlForList(resp.body);
    let total = parseHtmlForTotalPages(resp.body);
    return {
        list: list,
        page: parseInt(pg),
        pagecount: total,
        total: total * 20
    };
}

async function detailContent(ids) {
    let resp = await Java.req(ids[0]);
    let detail = parseHtmlForDetail(resp.body);
    detail.vod_id = ids[0];
    return { list: [detail] };
}

async function searchContent(key, quick, pg) {
    let url = baseUrl + '/vodsearch/' + encodeURIComponent(key) + '----------' + pg + '---.html';
    let resp = await Java.req(url);
    return {
        list: parseHtmlForList(resp.body),
        page: parseInt(pg),
        pagecount: parseHtmlForTotalPages(resp.body),
        total: parseHtmlForTotalPages(resp.body) * 20
    };
}

async function playerContent(flag, id) {
    let resp = await Java.req(id);
    let html = resp.body;
    let m3u8 = '';
    let idx = html.indexOf('"url":"');
    if (idx > -1) {
        let start = idx + 6;
        let end = html.indexOf('"', start);
        m3u8 = html.substring(start, end);
    }
    if (m3u8 && m3u8.indexOf('.m3u8') > -1) {
        return { type: 'direct', url: m3u8 };
    }
    return { type: 'sniff', url: id, keyword: '.m3u8|.mp4' };
}

function parseHtmlForList(html) {
    let vods = [];
    // 匹配每个视频项
    let itemRegex = /<li[^>]*class="[^"]*col-md-6[^"]*"[^>]*>([\s\S]*?)<\/li>/gi;
    let match;
    while ((match = itemRegex.exec(html)) !== null) {
        let itemHtml = match[1];
        
        // 提取详情页链接
        let linkMatch = itemHtml.match(/href="([^"]*\/voddetail\/[^"]*)"/);
        if (!linkMatch) continue;
        let href = linkMatch[1];
        
        // 提取标题
        let titleMatch = itemHtml.match(/title="([^"]*)"/);
        let title = titleMatch ? titleMatch[1] : '';
        if (!title) {
            let altMatch = itemHtml.match(/alt="([^"]*)"/);
            title = altMatch ? altMatch[1] : '';
        }
        
        // 提取图片
        let imgMatch = itemHtml.match(/data-original="([^"]*)"/);
        let pic = imgMatch ? imgMatch[1] : '';
        
        // 提取备注（集数/清晰度）
        let remarkMatch = itemHtml.match(/pic-text[^>]*>([^<]*)</);
        let remark = remarkMatch ? remarkMatch[1].trim() : '';
        
        if (href && title) {
            vods.push({
                vod_id: baseUrl + href,
                vod_name: title.trim(),
                vod_pic: pic,
                vod_remarks: remark
            });
        }
    }
    return vods;
}

function parseHtmlForDetail(html) {
    // 标题
    let titleMatch = html.match(/<h1[^>]*class="[^"]*title[^"]*"[^>]*>[\s\S]*?<span[^>]*>([^<]*)<\/span>/);
    let title = titleMatch ? titleMatch[1] : '';
    
    // 图片
    let imgMatch = html.match(/<img[^>]*class="[^"]*lazyload[^"]*"[^>]*data-original="([^"]*)"/);
    let pic = imgMatch ? imgMatch[1] : '';
    
    // 简介
    let descMatch = html.match(/<div[^>]*id="desc"[^>]*>[\s\S]*?<div[^>]*class="[^"]*col-pd[^"]*"[^>]*>([\s\S]*?)<\/div>/);
    let desc = descMatch ? descMatch[1].replace(/<[^>]*>/g, '').trim() : '';
    
    // 导演
    let director = '';
    let directorMatch = html.match(/导演[：:][\s\S]*?<a[^>]*>([^<]*)<\/a>/);
    if (directorMatch) director = directorMatch[1];
    
    // 主演
    let actor = '';
    let actorMatch = html.match(/主演[：:][\s\S]*?<a[^>]*>([^<]*)<\/a>/);
    if (actorMatch) actor = actorMatch[1];
    
    // 播放列表
    let playUrl = '';
    let playFrom = '';
    let playRegex = /<li[^>]*><a[^>]*href="([^"]*\/vodplay\/[^"]*)"[^>]*>([^<]*)<\/a><\/li>/gi;
    let playMatch;
    let urls = [];
    while ((playMatch = playRegex.exec(html)) !== null && urls.length < 200) {
        urls.push(playMatch[2] + '$' + baseUrl + playMatch[1]);
    }
    if (urls.length) {
        playUrl = urls.join('#');
        playFrom = '云播资源';
    }
    
    return {
        vod_name: title,
        vod_pic: pic,
        vod_content: desc,
        vod_director: director,
        vod_actor: actor,
        vod_play_from: playFrom,
        vod_play_url: playUrl
    };
}

function parseHtmlForTotalPages(html) {
    let lastMatch = html.match(/href="[^"]*--------(\d+)---\.html"[^>]*>尾页</);
    if (lastMatch) {
        return parseInt(lastMatch[1]);
    }
    return 1;
}