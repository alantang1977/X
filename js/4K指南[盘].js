/*
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '4K指南[盘]',
  author: 'EylinSir',
  lang: 'cat'
})
*/

// 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
// 严禁将其用于任何商业用途，下载后请于 24 小时内删除。

let host = 'https://4kzn.com';
const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Referer': host + '/'
};

async function init(cfg) {
    if (cfg.ext && cfg.ext.startsWith('http')) host = cfg.ext.trim().replace(/\/$/, '');
}

async function home(filter) {
    return JSON.stringify({
        class: [
            { type_id: 'zuixin', type_name: '最新' },
            { type_id: 'top250', type_name: 'TOP250' },
            { type_id: 'dianying', type_name: '电影' },
            { type_id: 'juji', type_name: '剧集' }
        ],
        filters: {
            "dianying": [{ key: "type", name: "类型", value: [{ "n": "全部", "v": "" }, { "n": "电影", "v": "dianying" }, { "n": "喜剧", "v": "xiju" }, { "n": "爱情", "v": "aiqing" }, { "n": "剧情", "v": "juqing" }, { "n": "悬疑", "v": "xuanyi" }, { "n": "传记", "v": "zhuanji" }, { "n": "动作", "v": "dongzuo" }, { "n": "科幻", "v": "kehuan" }, { "n": "犯罪", "v": "fanzui" }, { "n": "奇幻", "v": "qihuan" }, { "n": "冒险", "v": "maoxian" }, { "n": "家庭", "v": "jiating" }, { "n": "运动", "v": "yundong" }, { "n": "歌舞", "v": "gewu" }, { "n": "战争", "v": "zhanzheng" }, { "n": "惊悚", "v": "jingsong" }, { "n": "西部", "v": "xibu" }, { "n": "动画", "v": "donghua" }, { "n": "灾难", "v": "zainan" }, { "n": "恐怖", "v": "kongbu" }, { "n": "历史", "v": "lishi" }, { "n": "音乐", "v": "yinyue" }, { "n": "同性", "v": "tongxing" }, { "n": "纪录片", "v": "jilupian" }, { "n": "古装", "v": "guzhuang" }, { "n": "儿童", "v": "ertong" }, { "n": "武侠", "v": "武侠" }] }],
            "juji": [{ key: "type", name: "类型", value: [{ "n": "全部", "v": "" }, { "n": "剧集", "v": "juji" }, { "n": "剧情", "v": "juq" }, { "n": "惊悚", "v": "jings" }, { "n": "犯罪", "v": "fanzuii" }, { "n": "动作", "v": "jjdongzuo" }, { "n": "历史", "v": "jjlishi" }, { "n": "战争", "v": "jjzhanzheng" }, { "n": "冒险", "v": "jjmaoxian" }, { "n": "古装", "v": "古装" }, { "n": "爱情", "v": "爱情" }, { "n": "喜剧", "v": "喜剧" }, { "n": "最新", "v": "zuixin-juji" }, { "n": "科幻", "v": "科幻" }, { "n": "悬疑", "v": "悬疑" }, { "n": "奇幻", "v": "奇幻" }, { "n": "家庭", "v": "家庭" }, { "n": "恐怖", "v": "恐怖" }, { "n": "西部", "v": "西部" }, { "n": "动画", "v": "动画" }] }]
        }
    });
}

async function homeVod() {
    return await category('zuixin', 1, null, {});
}

async function category(tid, pg, filter, extend) {
    const url = `${host}/books/${(extend && extend.type) || tid}/page/${pg}`;
    const html = (await req(url, { headers })).content;
    const list = pdfa(html, '.posts-row .posts-item').map(it => ({
        vod_id: pdfh(it, 'a.item-image&&href'),
        vod_name: pdfh(it, '.item-title&&Text'),
        vod_pic: pdfh(it, '.lazy&&data-src'),
        vod_remarks: pdfh(it, '.text-muted&&Text')
    }));
    return JSON.stringify({ list, page: parseInt(pg), pagecount: 999, limit: 20, total: 999 });
}

async function search(wd, quick, pg = 1) {
    const url = `${host}/?post_type=book&s=${encodeURIComponent(wd)}&page=${pg}`;
    const html = (await req(url, { headers })).content;
    const list = pdfa(html, '.posts-row .posts-item').map(it => ({
        vod_id: pdfh(it, 'a.item-image&&href'),
        vod_name: pdfh(it, '.item-title&&Text'),
        vod_pic: pdfh(it, '.lazy&&data-src'),
        vod_remarks: pdfh(it, '.text-muted&&Text')
    }));

    return JSON.stringify({ list, page: parseInt(pg) });
}

async function detail(id) {
    const url = id.startsWith('http') ? id : host + id;
    const html = (await req(url, { headers })).content;
    const txt = pdfh(html, '.panel-body p&&Text');
    const get = (k) => (txt.match(new RegExp(`${k}:\\s*(.*?)(?=\\s*(导演|主演|类型|制片|语言|上映|片长|又名|IMDb|$))`)) || ['',''])[1].replace(/\//g, ',');
    const playList = pdfa(html, '.site-go a').map(a => 
        pdfh(a, 'a&&Text') + '$push://' + pdfh(a, 'a&&href')
    );

    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: pdfh(html, '.site-name&&Text'),
            vod_pic: pdfh(html, '.lazy&&data-src'),
            type_name: get('类型'),
            vod_year: (get('上映日期').match(/\d{4}/) || [''])[0],
            vod_area: get('制片国家/地区'),
            vod_actor: get('主演'),
            vod_director: get('导演'),
            vod_content: txt.split('IMDb:').pop().trim(),
            vod_play_from: playList.length ? playList.map(u => u.split('$')[0]).join('$$$') : '无资源',
            vod_play_url: playList.length ? playList.join('$$$') : ''
        }]
    });
}

async function play(flag, id, flags) {
    return JSON.stringify({ parse: 0, url: id });
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, search, detail, play };
}
