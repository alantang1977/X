const host = 'https://api.dbokutv.com';
const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.duboku.tv/"
};

function base64Encode(text) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let b64 = '';
    for (let i = 0; i < text.length; i += 3) {
        let n = (text.charCodeAt(i) << 16) | (text.charCodeAt(i + 1) << 8) | text.charCodeAt(i + 2);
        b64 += chars.charAt((n >> 18) & 63)
            + chars.charAt((n >> 12) & 63)
            + chars.charAt((n >> 6) & 63)
            + chars.charAt(n & 63);
    }
    let mod = text.length % 3;
    return (mod ? b64.slice(0, mod - 3) + "===".substring(mod) : b64);
}

function base64Decode(str) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    str = str.replace(/=/g, '');
    let bin = '';
    for (let i = 0; i < str.length; i += 4) {
        let n = (chars.indexOf(str.charAt(i)) << 18)
            | (chars.indexOf(str.charAt(i + 1)) << 12)
            | (chars.indexOf(str.charAt(i + 2)) << 6)
            | chars.indexOf(str.charAt(i + 3));
        bin += String.fromCharCode((n >> 16) & 255, (n >> 8) & 255, n & 255);
    }
    return bin.replace(/\0/g, '');
}

function decodeData(data) {
    if (!data || typeof data !== 'string') return '';
    let strippedStr = data.replace(/['"]/g, '').trim();
    if (!strippedStr) return '';
    let segmentLength = 10;
    let processedBase64 = '';
    for (let i = 0; i < strippedStr.length; i += segmentLength) {
        let segment = strippedStr.substring(i, i + segmentLength);
        processedBase64 += segment.split('').reverse().join('');
    }
    processedBase64 = processedBase64.replace(/\./g, '=');
    try {
        return base64Decode(processedBase64);
    } catch (e) {
        return '';
    }
}

function getSignedUrl(path) {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const randomNumber = Math.floor(Math.random() * 800000001);
    const valueA = (randomNumber + 100000000).toString();
    const valueB = (900000000 - randomNumber).toString();
    const combined = valueA + valueB;

    let interleaved = '';
    let minLen = Math.min(combined.length, timestamp.length);
    for (let i = 0; i < minLen; i++) {
        interleaved += combined[i] + timestamp[i];
    }
    interleaved += combined.substring(minLen) + timestamp.substring(minLen);

    const ssid = base64Encode(interleaved).replace(/=/g, '.');

    function randomStr(len) {
        const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let res = '';
        for (let i = 0; i < len; i++) res += chars.charAt(Math.floor(Math.random() * chars.length));
        return res;
    }

    const sign = randomStr(60);
    const token = randomStr(38);
    const connector = path.includes('?') ? '&' : '?';
    return `${host}${path}${connector}sign=${sign}&token=${token}&ssid=${ssid}`;
}

async function init(cfg) {}

async function home(filter) {
    const classes = [
        { type_id: '2', type_name: '连续剧' },
        { type_id: '1', type_name: '电影' },
        { type_id: '3', type_name: '综艺' },
        { type_id: '4', type_name: '动漫' }
    ];
    return JSON.stringify({ class: classes });
}

async function homeVod() {
    const url = getSignedUrl('/home');
    const r = await req(url, { headers });
    const json = JSON.parse(r.content);
    let videos = [];
    json.forEach(group => {
        (group.VodList || []).forEach(j => {
            videos.push({
                vod_id: decodeData(j.DId || j.DuId),
                vod_name: j.Name,
                vod_pic: decodeData(j.TnId),
                vod_remarks: j.Tag
            });
        });
    });
    return JSON.stringify({ list: videos });
}

async function category(tid, pg, filter, extend = {}) {
    let page = pg || 1;
    let pageStr = page.toString() === '1' ? '' : page.toString();
    let urlPath = `/vodshow/${tid}--------${pageStr}---`;
    const url = getSignedUrl(urlPath);
    const r = await req(url, { headers });
    const json = JSON.parse(r.content);

    let videos = (json.VodList || []).map(i => ({
        vod_id: decodeData(i.DId || i.DuId),
        vod_name: i.Name,
        vod_pic: decodeData(i.TnId),
        vod_remarks: i.Tag
    }));

    let pageCount = page;
    try {
        (json.PaginationList || []).forEach(j => {
            if (j.Type === 'StartEnd') {
                let parts = decodeData(j.PId || j.PuId).split('-');
                if (parts.length > 8) pageCount = parseInt(parts[8]);
            } else if (j.Type === 'ShortPage') {
                pageCount = parseInt(j.Name.split('/')[1]);
            }
        });
    } catch (e) {}

    return JSON.stringify({
        page: parseInt(page),
        pagecount: pageCount || parseInt(page),
        list: videos
    });
}

async function detail(id) {
    const url = getSignedUrl(id);
    const r = await req(url, { headers });
    const data = JSON.parse(r.content);

    const playUrls = (data.Playlist || []).map(i => {
        return `${i.EpisodeName}$${decodeData(i.VId)}`;
    }).join('#');

    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: data.Name,
            vod_pic: decodeData(data.TnId),
            vod_remarks: `评分：${data.Rating}`,
            vod_year: data.ReleaseYear,
            vod_area: data.Region,
            vod_actor: Array.isArray(data.Actor) ? data.Actor.join(',') : data.Actor,
            vod_director: data.Director,
            vod_content: data.Description,
            vod_play_from: '独播库',
            vod_play_url: playUrls,
            type_name: `${data.Genre || ''},${data.Scenario || ''}`
        }]
    });
}

async function search(wd, quick, pg = 1) {
    const url = getSignedUrl('/vodsearch') + `&wd=${encodeURIComponent(wd)}`;
    const r = await req(url, { headers });
    const json = JSON.parse(r.content);

    const list = (json || []).map(i => ({
        vod_id: decodeData(i.DId || i.DuId),
        vod_name: i.Name,
        vod_pic: decodeData(i.TnId),
        vod_remarks: i.Tag
    }));

    return JSON.stringify({ page: pg, list: list });
}

async function play(flag, id, flags) {
    const url = getSignedUrl(id);
    const r = await req(url, { headers });
    const res = JSON.parse(r.content);

    return JSON.stringify({
        parse: 0,
        url: decodeData(res.HId),
        header: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': 'https://w.duboku.io',
            'Referer': 'https://w.duboku.io/'
        }
    });
}

export default { init, home, homeVod, category, detail, search, play };