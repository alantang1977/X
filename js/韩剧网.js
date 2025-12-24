/*
by:EylinSir
*/

let host = 'https://hanju51.com';
let headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": host + "/"
};

function extractVideos(html, limit = 0) {
    let videos = [];
    let liPattern = /<li class="fed-list-item[^>]*>([\s\S]*?)<\/li>/gs;
    let match;

    while ((match = liPattern.exec(html)) !== null && (!limit || videos.length < limit)) {
        let item = match[1];
        let vod_id = (item.match(/href="\/voddetail\/(\w+)/) || [])[1] || "";
        let vod_name = (item.match(/>([^<]+)<\/a>/) || [])[1] || "";
        let vod_pic = (item.match(/data-original="([^"]+)"/) || [])[1] || "";
        let vod_remarks = (item.match(/<span class="fed-list-remarks[^>]*>([^<]+)<\/span>/) || [])[1] || "";

        if (!vod_id || !vod_name || !vod_pic) continue;
        if (vod_name.includes('更多') || vod_name.includes('韩剧网')) continue;

        videos.push({
            vod_id: vod_id.trim(),
            vod_name: vod_name.trim(),
            vod_remarks: vod_remarks.trim(),
            vod_pic: vod_pic.startsWith('http') ? vod_pic : host + vod_pic
        });
    }
    return videos;
}

async function home(filter) {
    let resp = await req(host, { headers });
    let list = resp?.content ? extractVideos(resp.content) : [];
    return JSON.stringify({
        class: [
            { type_id: "1", type_name: "韩剧" },
            { type_id: "2", type_name: "韩影" },
            { type_id: "3", type_name: "韩综" }
        ],
        filters: {},
        list
    });
}

async function category(tid, pg, filter, extend) {
    let types = ['hanguodianshiju', 'hanguodianying', 'hanguozongyi'];
    let type = types[tid - 1] || types[0];
    let url = `${host}/vodtype/${type}-${pg}/`;
    let html = (await req(url, { headers })).content || '';
    let list = extractVideos(html);
    let pagecount = html.match(/\/(\d+)\/<\/a>\s*<a[^>]*>\.\.\.<\/a>/)?.[1] ? parseInt(html.match(/\/(\d+)\/<\/a>\s*<a[^>]*>\.\.\.<\/a>/)[1]) : 999;

    return JSON.stringify({ list, page: parseInt(pg || 1), pagecount, limit: 20 });
}

async function detail(id) {
    let html = (await req(`${host}/voddetail/${id}/`, { headers })).content || '';
    if (!html) return JSON.stringify({ list: [] });

    let sources = [...html.matchAll(/<a[^>]*class="fed-tabs-btn[^"]*"[^>]*>([^<]+)<\/a>/g)].map(m => m[1].trim());
    let blocks = [...html.matchAll(/<ul class="fed-tabs-btm[^>]*>([\s\S]*?)<\/ul>/g)].map(m => m[1]);
    let playFrom = [], playUrl = [];
    for (let i = 0; i < sources.length && i < blocks.length; i++) {
        let eps = [...blocks[i].matchAll(/<a[^>]*href="\/vodplay\/([^"]+)[^>]*>([^<]+)<\/a>/g)];
        if (eps.length) {
            playFrom.push(sources[i]);
            playUrl.push(eps.map(e => e[2].trim() + '$' + e[1].trim()).join('#'));
        }
    }

    if (playFrom.length === 0) return JSON.stringify({ list: [] });
    let vod_name = pdfh(html, "h1&&Text") || "";
    let vod_pic = (html.match(/data-original="([^"]+)"/) || [])[1] || "";
    if (vod_pic && !vod_pic.startsWith('http')) vod_pic = host + vod_pic;
    let vod_content = (html.match(/<p class="fed-conv-text[^>]*>([\s\S]*?)<\/p>/s) || [])[1]?.replace(/<[^>]+>/g, "") || "暂无简介";
    let vod_year = (html.match(/(20\d{2})/) || [])[1] || "";
    let extract = (label) => {
        let m = html.match(new RegExp(`<span class="fed-text-muted">${label}：</span>([\\s\\S]*?)<\\/li>`));
        return m ? [...m[1].matchAll(/<a[^>]*>([^<]+)<\/a>/g)].map(x => x[1]).join(" / ") : "";
    };

    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name,
            vod_pic,
            vod_content,
            vod_year,
            vod_director: extract("导演"),
            vod_actor: extract("主演"),
            vod_play_from: playFrom.join('$$$'),
            vod_play_url: playUrl.join('$$$')
        }]
    });
}

async function play(flag, id, flags) {
    return JSON.stringify({
        parse: 1,
        url: `${host}/vodplay/${id}/`,
        header: headers
    });
}

export default { home, category, detail, play };
