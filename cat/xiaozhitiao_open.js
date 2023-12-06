import { load, _ } from 'assets://js/lib/cat.js';
import { log } from './lib/utils.js';
import { initAli, detailContent, playContent } from './lib/ali.js';

let siteKey = 'xiaozhitiao';
let siteType = 0;
let siteUrl = 'https://gitcafe.net/tool/alipaper/';
let aliUrl = "https://www.aliyundrive.com/s/";
let token = '';
let date = new Date();

const UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1';

async function request(reqUrl, data) {
    let res = await req(reqUrl, {
        method: 'post',
        headers: {
            'User-Agent': UA,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data: data,
        postType: 'form',
    });
    return res.content;
}

// cfg = {skey: siteKey, ext: extend}
async function init(cfg) {
    try {
        siteKey = _.isEmpty(cfg.skey) ? '' : cfg.skey;
        siteType = _.isEmpty(cfg.stype) ? '' : cfg.stype;
        await initAli(cfg);
    } catch (e) {
        await log('init:' + e.message + ' line:' + e.lineNumber);
    }
}

async function home(filter) {
    return '{}';
}

async function homeVod() {}

async function category(tid, pg, filter, extend) {
    return '{}';
}

async function detail(id) {
    try {
        return await detailContent(id);
    } catch (e) {
        await log('detail:' + e.message + ' line:' + e.lineNumber);
    }
}

async function play(flag, id, flags) {
    try {
        return await playContent(flag, id, flags);
    } catch (e) {
        await log('play:' + e.message + ' line:' + e.lineNumber);
    }
}

async function search(wd, quick, pg) {
    if (pg <= 0) pg = 1;
    const params = {
        "action": "search",
        "from": "web",
        "keyword": wd,
        "token": await getToken(),
    };
    const resp = await request(siteUrl, params);
    const json = JSON.parse(resp);
    if (!json.success) return "";
    const videos = _.map(json.data, (item) => {
        return {
            vod_id: aliUrl + item.alikey,
            vod_name: item.title,
            vod_pic: "https://www.lgstatic.com/i/image2/M01/15/7E/CgoB5lysLXCADg6ZAABapAHUnQM321.jpg",
            vod_remarks: item.creatime
        };
    });
    return JSON.stringify({
        list: videos,
    });
}

async function getToken() {
    const newDate = new Date();
    if (_.isEmpty(token) || newDate > date) {
        const params = {
            "action": "get_token",
        };
        const resp = await request(siteUrl, params);
        const json = JSON.parse(resp);
        if (json.success) {
            token = json.data;
            date = newDate;
        }
    }
    return token;
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        detail: detail,
        play: play,
        search: search,
    };
}