let host = 'https://www.guipian360.com';
let headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": host + "/"
};

const extractVideos = html => {
    if (!html) return [];
    return pdfa(html, '.m-movies .u-movie').map(it => {
        const url = it.match(/href="([^"]+)"/)?.[1] || "";
        const id = url.match(/\/(\d+)\.html/)?.[1];
        let name = it.match(/title="([^"]+)"/)?.[1] || "";
        name = name.split('/')[0].trim().replace(/.*《([^》]+)》.*/, "$1");
        const pic = it.match(/src="([^"]+)"/)?.[1] || "";
        const remarks = it.match(/class="zhuangtai"[^>]*>([^<]+)/)?.[1] || "";
        return id && name ? {
            vod_id: id,
            vod_name: name,
            vod_pic: pic.startsWith('/') ? host + pic : pic,
            vod_remarks: remarks.trim()
        } : null;
    }).filter(Boolean);
};

const home = async () => {
    const list = extractVideos((await req(host, { headers }))?.content || '');
    return JSON.stringify({
        class: [
            {type_id:"1",type_name:"鬼片大全"},{type_id:"6",type_name:"大陆鬼片"},{type_id:"9",type_name:"港台鬼片"},
            {type_id:"8",type_name:"林正英鬼片"},{type_id:"7",type_name:"日韩鬼片"},{type_id:"11",type_name:"欧美鬼片"},
            {type_id:"10",type_name:"泰国鬼片"},{type_id:"3",type_name:"恐怖片"},{type_id:"2",type_name:"电视剧"},
            {type_id:"12",type_name:"国产剧"},{type_id:"20",type_name:"港台剧"},{type_id:"13",type_name:"美剧"},
            {type_id:"14",type_name:"韩剧"},{type_id:"15",type_name:"日剧"},{type_id:"16",type_name:"泰剧"},
            {type_id:"22",type_name:"其它剧"},{type_id:"4",type_name:"动漫"}
        ],
        filters: {},
        list
    });
};

const homeVod = async () => {
    const list = extractVideos((await req(host, { headers }))?.content || '');
    return JSON.stringify({ list });
};

const category = async (tid, pg, _, extend) => {
    const url = pg > 1 ? `${host}/list/${tid}_${pg}.html` : `${host}/list/${tid}.html`;
    const html = (await req(url, { headers }))?.content || '';
    const list = extractVideos(html);
    const m = html.match(/href="\/list\/\d+_(\d+)\.html"[^>]*>\.\.(\d+)<\/a>/);
    return JSON.stringify({ list, page: +pg, pagecount: m ? +m[1] : 999, limit: 20 });
};

const detail = async id => {
    const html = (await req(`${host}/nv/${id}.html`, { headers }))?.content || '';
    if (!html) return JSON.stringify({ list: [] });

    const tabs = pdfa(html, '#tv_tab li a').map(a => (a.match(/>([^<]+)/)?.[1] || "线路").trim());
    const urls = pdfa(html, '#tv_tab .list').map(list =>
        pdfa(list, 'ul.abc li a').map(a => {
            const name = (a.match(/>([^<]+)/)?.[1] || "播放").trim();
            const vid = (a.match(/href="\/play\/(.*?)\.html"/)?.[1] || "");
            return `${name}$${vid}`;
        }).join('#')
    );

    if (!tabs.length || !urls.length) return JSON.stringify({ list: [] });

    let vod_name = (html.match(/<h1>(.*?)<\/h1>/)?.[1] || "").split('/')[0].trim().replace(/.*《([^》]+)】?.*/, "$1");
    const m = s => (html.match(s) || ["", ""])[1].trim();
    const vod_pic = m(/<img[^>]+src="([^"]+)"[^>]*class="lazy"/);
    const vod_content = (html.match(/<p class="jianjie-p"[^>]*>([\s\S]*?)<\/p>/)?.[1] || "").replace(/<.*?>/g, "").trim() || "暂无简介";

    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name,
            vod_pic: vod_pic.startsWith('/') ? host + vod_pic : vod_pic,
            vod_content,
            vod_director: m(/<li class="hidden-xs"><span>导演：<\/span>(.*?)<\/li>/),
            vod_actor: m(/<li class="hidden-xs"><span>主演：<\/span>(.*?)<\/li>/),
            vod_year: m(/<strong>(\d{4})年<\/strong>/),
            vod_area: m(/地区：<\/span><a[^>]*>(.*?)<\/a>/),
            vod_lang: m(/语言：<\/span>(.*?)<\/li>/),
            vod_play_from: tabs.join('$$$'),
            vod_play_url: urls.join('$$$')
        }]
    });
};

const search = async (wd, _, pg = 1) => {
    const url = `${host}/vodsearch/${encodeURIComponent(wd)}----------${pg}---.html`;
    const list = extractVideos((await req(url, { headers }))?.content || '');
    return JSON.stringify({ list });
};

const play = async (_, id) => {
    const html = (await req(`${host}/play/${id}.html`, { headers }))?.content || '';
    const m3u8 = html.match(/var now="([^"]+)";/);
    return JSON.stringify({
        parse: m3u8 ? 0 : 1,
        url: m3u8 ? m3u8[1] : `${host}/play/${id}.html`,
        header: headers
    });
};

export default {
    init: async () => {},
    home,
    homeVod,
    category,
    detail,
    search,
    play
};
