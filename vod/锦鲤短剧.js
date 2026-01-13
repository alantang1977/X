/**
 * 锦鲤短剧 爬虫
 * 版本：3.0 - WvSpider v2.0 新架构
 * 最后更新：2025-12-23
 * 发布页 https://www.jinlidj.com/
 *
 * @config
 * debug: true
 *
 */

const baseUrl = 'https://api.jinlidj.com';

/**
 * 初始化方法
 */
function init(cfg) {
    return {};
}

/**
 * 首页分类
 */
async function homeContent(filter) {
    const filterConfig = {
        class: [
            { type_id: "1", type_name: "情感关系" },
            { type_id: "2", type_name: "成长逆袭" },
            { type_id: "3", type_name: "奇幻异能" },
            { type_id: "4", type_name: "战斗热血" },
            { type_id: "5", type_name: "伦理现实" },
            { type_id: "6", type_name: "时空穿越" },
            { type_id: "7", type_name: "权谋身份" }
        ]
	};
    return filterConfig;
}

/**
 * 首页推荐视频
 */
async function homeVideoContent() {
    return {};
}

/**
 * 分类列表
 */
async function categoryContent(tid, pg, filter, extend) {
    const res = Java.req(baseUrl + '/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: pg, limit: 24, type_id: tid })
    });
    const data = JSON.parse(res.body).data;

    return { 
        code: 1, 
        msg: "数据列表", 
        list: data.list, 
        page: parseInt(pg) || 1, 
        pagecount: parseInt(data.total / 24), 
        limit: 24, 
        total: data.total
    };
}

/**
 * 详情页
 */
async function detailContent(ids) {
    const res = Java.req(baseUrl + '/api/detail/' + ids[0]);
    const data = JSON.parse(res.body).data;
    const player = data.player;
    const playUrlParts = [];
    for (const key in player) {
        playUrlParts.push(key + '$' + player[key] + '&auto=1');
    }
    const vod_play_url = playUrlParts.join('#');

    const vod = {
        "vod_id": data.vod_id,
        "vod_name": data.vod_name,
        "vod_tag": data.vod_tag,
        "vod_class": data.vod_class,
        "vod_pic": data.vod_pic,
        "vod_actor": data.vod_actor,
        "vod_director": data.vod_director || "",
        "vod_content": data.vod_blurb,
        "vod_area": data.vod_area,
        "vod_year": data.vod_year,
        "vod_play_from": "在线",
        "vod_play_url": vod_play_url
    };
    
    return { 
        code: 1, 
        msg: "数据列表", 
        list: [vod], 
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
    const res = Java.req(baseUrl + '/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: pg, limit: 24, keyword: key })
    });
    const data = JSON.parse(res.body).data;

    return { 
        code: 1, 
        msg: "数据列表", 
        list: data.list, 
        page: parseInt(pg) || 1, 
        pagecount: parseInt(data.total / 24), 
        limit: 24, 
        total: data.total
    };
}


/**
 * 播放器
 */
async function playerContent(flag, id, vipFlags) {
    return { url: id, parse: 1 };
}