let host = 'https://www.ylys.tv';
let headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": host + "/"
};

async function init(cfg) {}

function extractVideos(html, limit = 0) {
    let videos = [];
    let pattern = /<a href="\/voddetail\/(\d+)\/".*?title="([^"]+)".*?<div class="module-item-note">([^<]+)<\/div>.*?data-original="([^"]+)"/gs;
    let match;
    while ((match = pattern.exec(html)) !== null) {
        videos.push({
            vod_id: match[1].trim(),
            vod_name: match[2].trim(),
            vod_remarks: match[3].trim(),
            vod_pic: match[4].startsWith('/') ? host + match[4] : match[4]
        });
        if (limit && videos.length >= limit) break;
    }
    return videos;
}

async function home(filter) {
    let resp = await req(host, { headers });
    let list = resp?.content ? extractVideos(resp.content) : [];
    return JSON.stringify({
        class: [
            { type_id: "1", type_name: "电影" },
            { type_id: "2", type_name: "剧集" },
            { type_id: "3", type_name: "综艺" },
            { type_id: "4", type_name: "动漫" }
        ],
        "filters": {
            "1": [
                {"key":"class","name":"类型","value":[{"n":"全部","v":""},{"n":"动作片","v":"6"},{"n":"喜剧片","v":"7"},{"n":"爱情片","v":"8"},{"n":"科幻片","v":"9"},{"n":"恐怖片","v":"11"}]},
                {"key":"year","name":"年份","value":[{n:"全部",v:""},...Array.from({length:15},(_,i)=>{let y=2025-i;return{n:y+"",v:y+""}})]}
                ],
            "2": [
                {"key":"class","name":"类型","value":[{"n":"全部","v":""},{"n":"国产剧","v":"13"},{"n":"港台剧","v":"14"},{"n":"日剧","v":"15"},{"n":"韩剧","v":"33"},{"n":"欧美剧","v":"16"}]},
                {"key":"year","name":"年份","value":[{n:"全部",v:""},...Array.from({length:15},(_,i)=>{let y=2025-i;return{n:y+"",v:y+""}})]}
                ],
            "3": [
                {"key":"class","name":"类型","value":[{"n":"全部","v":""},{"n":"内地综艺","v":"27"},{"n":"港台综艺","v":"28"},{"n":"日本综艺","v":"29"},{"n":"韩国综艺","v":"36"}]},
                {"key":"year","name":"年份","value":[{n:"全部",v:""},...Array.from({length:15},(_,i)=>{let y=2025-i;return{n:y+"",v:y+""}})]}
                ],
            "4": [
                {"key":"class","name":"类型","value":[{"n":"全部","v":""},{"n":"国产动漫","v":"31"},{"n":"日本动漫","v":"32"},{"n":"欧美动漫","v":"42"},{"n":"其他动漫","v":"43"}]},
                {"key":"year","name":"年份","value":[{n:"全部",v:""},...Array.from({length:15},(_,i)=>{let y=2025-i;return{n:y+"",v:y+""}})]}
                ]
        },
        list: list
    });
}

async function category(tid, pg, filter, extend) {
    let url = `${host}/vodshow/${extend?.class || tid}--------${pg}---${extend?.year || ''}/`;
    let html = (await req(url, { headers }))?.content || '';
    let list = html ? extractVideos(html) : [];
    let m = html.match(/\/vodshow\/[^-]*-{8}(\d+)-{3}/);
    return JSON.stringify({ list, page: +pg, pagecount: m ? +m[1] : 999, limit: 20 });
}

async function detail(id) {
    let html = (await req(host + '/voddetail/' + id + '/', { headers })).content || '';
    if (!html) return JSON.stringify({ list: [] });
    
    let playFrom = pdfa(html, "div.module-tab-item").map(it =>
        (pdfh(it, "span&&Text") || "线路")
    ).join('$$$');

    let playUrl = pdfa(html, "div.module-play-list-content").map(list =>
        pdfa(list, "a").map(a => {
            let name = pdfh(a, "span&&Text") || "播放";
            let href = pdfh(a, "a&&href") || "";
            let vid = href.replace(/.*?\/play\/(.*?)\/.*/, "$1");
            return name + '$' + vid;
        }).join('#')
    ).join('$$$');

    if (!playFrom || !playUrl) return JSON.stringify({ list: [] });

    let vod_name = pdfh(html, "h1&&Text") || "";
    let vod_pic = pdfh(html, "div.module-item-pic&&data-original") ||
                  pdfh(html, "img&&data-src") ||
                  pdfh(html, "img&&src") || "";
    if (vod_pic && vod_pic.startsWith('/')) vod_pic = host + vod_pic;

    let vod_content = (html.match(/introduction-content">.*?<p>(.*?)<\/p>/s) || ["", ""])[1]?.replace(/<[^>]+>/g, "") || "暂无简介";
    let vod_year = (html.match(/href="\/vodshow\/\d+-----------(\d{4})\//) || ["", ""])[1] || "";
    let vod_director = (html.match(/导演：.*?<a[^>]*>([^<]+)<\/a>/) || ["", ""])[1] || "";
    let vod_actor = [...html.matchAll(/主演：.*?<a[^>]*>([^<]+)<\/a>/g)]
        .map(m => m[1]).filter(Boolean).join(" / ");

    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name,
            vod_pic,
            vod_content,
            vod_year,
            vod_director,
            vod_actor,
            vod_play_from: playFrom,
            vod_play_url: playUrl
        }]
    });
}

async function play(flag, id, flags) {
    return JSON.stringify({
        parse: 1,
        url: host + "/play/" + id + "/",
        header: headers
    });
}

export default { init, home, category, detail, play };
