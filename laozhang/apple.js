let host = 'http://asp.xpgtv.com';
let headers = {
    "User-Agent": "okhttp/3.12.11"
};

async function init(cfg) {}

function getList(data) {
    let videos = [];
    data.forEach(vod => {
        let r = vod.updateInfo ? "更新至" + vod.updateInfo : "";
        videos.push({
            "vod_id": vod.id.toString(),
            "vod_name": vod.name,
            "vod_pic": vod.pic,
            "vod_remarks": r || (vod.score ? vod.score.toString() : "")
        });
    });
    return videos;
}

// ------------------- 兼容 JSON -------------------
function parseResp(resp) {
    return typeof resp.content === "string" ? JSON.parse(resp.content) : resp.content;
}

async function home(filter) {
    let url = host + "/api.php/v2.vod/androidtypes";
    let resp = await req(url, { headers: headers });
    let data = parseResp(resp);

    let dy = { "classes": "类型", "areas": "地区", "years": "年份", "sortby": "排序" };
    let demos = ['时间', '人气', '评分'];
    let classes = [];
    let filters = {};

    data.data.forEach(item => {
        let typeId = item.type_id.toString();
        classes.push({ "type_name": item.type_name, "type_id": typeId });
        item['sortby'] = ['updatetime', 'hits', 'score'];
        let filterArray = [];
        for (let key in dy) {
            if (item[key] && item[key].length > 1) {
                let values = [];
                item[key].forEach((val, idx) => {
                    let vStr = val.toString().trim();
                    if (vStr !== "") {
                        values.push({ "n": key === "sortby" ? demos[idx] : vStr, "v": vStr });
                    }
                });
                let fKey = key === "areas" ? "areaes" : (key === "years" ? "yeares" : key);
                filterArray.push({ "key": fKey, "name": dy[key], "value": values });
            }
        }
        filters[typeId] = filterArray;
    });
    return JSON.stringify({ class: classes, filters: filters });
}

async function homeVod() {
    let url = host + "/api.php/v2.main/androidhome";
    let resp = await req(url, { headers: headers });
    let data = parseResp(resp);

    let videos = [];
    data.data.list.forEach(i => { videos = videos.concat(getList(i.list)); });
    return JSON.stringify({ list: videos });
}

async function category(tid, pg, filter, extend) {
    let params = { 
        "page": pg, 
        "type": tid, 
        "area": extend.areaes || '', 
        "year": extend.yeares || '', 
        "sortby": extend.sortby || '', 
        "class": extend.classes || '' 
    };
    let query = Object.keys(params).filter(k => params[k] !== '').map(k => k + '=' + encodeURIComponent(params[k])).join('&');
    let url = host + '/api.php/v2.vod/androidfilter10086?' + query;
    let resp = await req(url, { headers: headers });
    let data = parseResp(resp);

    return JSON.stringify({ list: getList(data.data), page: parseInt(pg), pagecount: 9999, limit: 90, total: 999999 });
}

async function detail(id) {
    let url = host + '/api.php/v3.vod/androiddetail2?vod_id=' + id;
    let resp = await req(url, { headers: headers });
    let data = parseResp(resp).data;

    // 过滤掉包含“及时雨”的选集
    let filteredUrls = data.urls.filter(i => !i.key.includes("及时雨"));
    let playlist = filteredUrls.map(i => i.key + '$' + i.url).join('#');

    let vod = {
        'vod_id': id,
        'vod_name': data.name,
        'vod_year': data.year,
        'vod_area': data.area,
        'vod_lang': data.lang,
        'type_name': data.className,
        'vod_actor': data.actor,
        'vod_director': data.director,
        'vod_content': data.content,
        'vod_play_from': '书生精选线路', 
        'vod_play_url': playlist
    };

    return JSON.stringify({ list: [vod] });
}

async function search(wd, quick, pg) {
    let page = pg || '1';
    let url = host + '/api.php/v2.vod/androidsearch10086?page=' + page + '&wd=' + encodeURIComponent(wd);
    let resp = await req(url, { headers: headers });
    let data = parseResp(resp);

    return JSON.stringify({ list: getList(data.data), page: page });
}

async function play(flag, id, flags) {
    let playUrl = id;
    if (!id.startsWith('http')) {
        playUrl = "http://c.xpgtv.net/m3u8/" + id + ".m3u8";
    }

    const playHeader = {
        'user_id': 'XPGBOX',
        'token2': 'SnAXiSW8vScXE0Z9aDOnK5xffbO75w1+uPom3WjnYfVEA1oWtUdi2Ihy1N8=',
        'version': 'XPGBOX com.phoenix.tv1.5.7',
        'hash': 'd78a',
        'screenx': '2345',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'token': 'ElEDlwCVgXcFHFhddiq2JKteHofExRBUrfNlmHrWetU3VVkxnzJAodl52N9EUFS+Dig2A/fBa/V9RuoOZRBjYvI+GW8kx3+xMlRecaZuECdb/3AdGkYpkjW3wCnpMQxf8vVeCz5zQLDr8l8bUChJiLLJLGsI+yiNskiJTZz9HiGBZhZuWh1mV1QgYah5CLTbSz8=',
        'timestamp': '1743060300',
        'screeny': '1065',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    };

    return JSON.stringify({
        parse: 0,
        url: playUrl,
        header: playHeader
    });
}

export default { init, home, homeVod, category, detail, search, play };