let host = 'https://www.ylys.tv';
let headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": host + "/"
};

async function init(cfg) {}

function getList(html) {
    let videos = [];
    let items = pdfa(html, ".module-item");
    items.forEach(it => {
        let idMatch = it.match(/detail\/(\d+)/);
        let nameMatch = it.match(/title="(.*?)"/);
        let picMatch = it.match(/data-original="(.*?)"/);
        if (idMatch && nameMatch) {
            let vpic = picMatch ? picMatch[1] : "";
            if (vpic.startsWith('/')) vpic = host + vpic;
            videos.push({
                "vod_id": idMatch[1],
                "vod_name": nameMatch[1],
                "vod_pic": vpic,
                "vod_remarks": (it.match(/module-item-note">(.*?)<\/div>/) || ["", ""])[1].replace(/<.*?>/g, "")
            });
        }
    });
    return videos;
}

async function home(filter) {
    let classes = [{ "type_name": "电影", "type_id": "1" }, { "type_name": "剧集", "type_id": "2" }, { "type_name": "综艺", "type_id": "3" }, { "type_name": "动漫", "type_id": "4" }];
    return JSON.stringify({ class: classes });
}

async function homeVod() {
    let resp = await req(host, { headers: headers });
    return JSON.stringify({ list: getList(resp.content) });
}

async function category(tid, pg, filter, extend) {
    let p = pg || 1;
    let url = host + "/vodtype/" + tid + (p > 1 ? "/page/" + p + "/" : "/");
    let resp = await req(url, { headers: headers });
    return JSON.stringify({ list: getList(resp.content), page: parseInt(p) });
}

async function detail(id) {
    let url = host + '/voddetail/' + id + '/';
    let resp = await req(url, { headers: headers });
    let html = resp.content;
    let playFrom = [];
    let playUrl = [];
    let tabs = pdfa(html, ".module-tab-item");
    tabs.forEach(tab => {
        let name = tab.match(/<span>(.*?)<\/span>/);
        playFrom.push(name ? name[1] : "线路");
    });
    let lists = pdfa(html, ".module-play-list-content"); 
    lists.forEach(listHtml => {
        let links = pdfa(listHtml, "a");
        let eps = links.map(linkStr => {
            let nameMatch = linkStr.match(/<span>(.*?)<\/span>/);
            let hrefMatch = linkStr.match(/href="(.*?)"/);
            let name = nameMatch ? nameMatch[1] : "播放";
            let href = hrefMatch ? hrefMatch[1] : "";
            let epId = href.split('/').filter(Boolean).pop(); 
            return name + '$' + epId;
        });
        playUrl.push(eps.join('#'));
    });
    let vod = {
        'vod_id': id,
        'vod_name': (html.match(/<h1>(.*?)<\/h1>/) || ["", ""])[1].replace(/<.*?>/g, ""),
        'vod_pic': (html.match(/data-original="(.*?)"/) || ["", ""])[1],
        'vod_content': (html.match(/introduction-content">.*?<p>(.*?)<\/p>/s) || ["", ""])[1].replace(/<.*?>/g, ""),
        'vod_play_from': playFrom.join('$$$'),
        'vod_play_url': playUrl.join('$$$')
    };
    return JSON.stringify({ list: [vod] });
}

async function search(wd, quick, pg) {
    let url = host + '/vodsearch/' + encodeURIComponent(wd) + '-------------/';
    let resp = await req(url, { headers: headers });
    let videos = [];
    // 搜索页专用选择器对齐 py 逻辑
    let items = pdfa(resp.content, ".module-card-item");
    if (items.length === 0) items = pdfa(resp.content, ".module-search-item");
    
    items.forEach(it => {
        let idMatch = it.match(/detail\/(\d+)/);
        // 搜索页标题通常在 strong 标签或带有特定 class 的 div 中
        let nameMatch = it.match(/title="(.*?)"/) || it.match(/<strong>(.*?)<\/strong>/);
        let picMatch = it.match(/data-original="(.*?)"/) || it.match(/src="(.*?)"/);
        
        if (idMatch && nameMatch) {
            let vpic = picMatch ? picMatch[1] : "";
            if (vpic.startsWith('/')) vpic = host + vpic;
            videos.push({
                "vod_id": idMatch[1],
                "vod_name": nameMatch[1].replace(/<.*?>/g, ""),
                "vod_pic": vpic,
                "vod_remarks": (it.match(/module-item-note">(.*?)<\/div>/) || ["", "搜索结果"])[1].replace(/<.*?>/g, "")
            });
        }
    });
    return JSON.stringify({ list: videos });
}

async function play(flag, id, flags) {
    return JSON.stringify({
        parse: 1,
        url: host + "/play/" + id + "/",
        header: headers
    });
}

export default { init, home, homeVod, category, detail, search, play };
