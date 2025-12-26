async function init(cfg) {
    const ext = cfg.ext;
    cfg.skey = '';
    cfg.stype = '3';
}

function ensureVars(){
    console.log('typeof getProxy:', typeof getProxy);
    console.log('typeof base64Encode:', typeof base64Encode);
    console.log('typeof base64Decode:', typeof base64Decode);
    console.log('typeof JSON5:', typeof JSON5);
    console.log('typeof gzip:', typeof gzip);
    console.log('typeof ungzip:', typeof ungzip);
    console.log('typeof atob:', typeof atob);
    console.log('typeof btoa:', typeof btoa);
}

// let host = 'https://api.ubj83.com';
//let host = 'https://xqmbwc.zxbwv.com';
//let host = 'https://zlokzk.deweit.com';
//let host = 'https://ofxbny.qyjzlh.com';
//let host = 'https://ts5hto.qyjzlh.com';
// let host = 'https://ij1men.slsw6.com';
let host = 'https://api.ztcgi.com';

let UA = 'Mozilla/5.0 (Linux; Android 9; V2196A Build/PQ3A.190705.08211809; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36;webank/h5face;webank/1.0;netType:NETWORK_WIFI;appVersion:416;packageName:com.jp3.xg3';
let imghost = `https://${JSON.parse((await req(`${host}/api/appAuthConfig`)).content).data.imgDomain}`;

//分类数据
async function home(filter) {
    // console.log('typeof getProxy:', typeof getProxy);
    // if (typeof getProxy === 'function') {
    //     console.log('getProxy(true):', getProxy(true));
    // }
    // ensureVars();
    let classes = [{type_id: '1', type_name: '电影',}, {type_id: '2', type_name: '电视剧',}, {
        type_id: '3',
        type_name: '动漫',
    }, {type_id: '4', type_name: '综艺',}];

    let filterObj = {
        "1": [{
            "key": "cateId",
            "name": "分类",
            "value": [{"v": "1", "n": "剧情"}, {"v": "2", "n": "爱情"}, {"v": "3", "n": "动画"}, {
                "v": "4",
                "n": "喜剧"
            }, {"v": "5", "n": "战争"}, {"v": "6", "n": "歌舞"}, {"v": "7", "n": "古装"}, {
                "v": "8",
                "n": "奇幻"
            }, {"v": "9", "n": "冒险"}, {"v": "10", "n": "动作"}, {"v": "11", "n": "科幻"}, {
                "v": "12",
                "n": "悬疑"
            }, {"v": "13", "n": "犯罪"}, {"v": "14", "n": "家庭"}, {"v": "15", "n": "传记"}, {
                "v": "16",
                "n": "运动"
            }, {"v": "18", "n": "惊悚"}, {"v": "20", "n": "短片"}, {"v": "21", "n": "历史"}, {
                "v": "22",
                "n": "音乐"
            }, {"v": "23", "n": "西部"}, {"v": "24", "n": "武侠"}, {"v": "25", "n": "恐怖"}]
        }, {
            "key": "area",
            "name": "地區",
            "value": [{"v": "1", "n": "国产"}, {"v": "3", "n": "中国香港"}, {"v": "6", "n": "中国台湾"}, {
                "v": "5",
                "n": "美国"
            }, {"v": "18", "n": "韩国"}, {"v": "2", "n": "日本"}]
        }, {
            "key": "year",
            "name": "年代",
            "value": [{"v": "107", "n": "2025"}, {"v": "119", "n": "2024"}, {"v": "153", "n": "2023"}, {
                "v": "101",
                "n": "2022"
            }, {"v": "118", "n": "2021"}, {"v": "16", "n": "2020"}, {"v": "7", "n": "2019"}, {
                "v": "2",
                "n": "2018"
            }, {"v": "3", "n": "2017"}, {"v": "22", "n": "2016"}, {"v": "2015", "n": "2015以前"}]
        }, {
            "key": "sort",
            "name": "排序",
            "value": [{"v": "update", "n": "最新"}, {"v": "hot", "n": "最热"}, {"v": "rating", "n": "评分"}]
        }],
        "2": [{
            "key": "cateId",
            "name": "分类",
            "value": [{"v": "1", "n": "剧情"}, {"v": "2", "n": "爱情"}, {"v": "3", "n": "动画"}, {
                "v": "4",
                "n": "喜剧"
            }, {"v": "5", "n": "战争"}, {"v": "6", "n": "歌舞"}, {"v": "7", "n": "古装"}, {
                "v": "8",
                "n": "奇幻"
            }, {"v": "9", "n": "冒险"}, {"v": "10", "n": "动作"}, {"v": "11", "n": "科幻"}, {
                "v": "12",
                "n": "悬疑"
            }, {"v": "13", "n": "犯罪"}, {"v": "14", "n": "家庭"}, {"v": "15", "n": "传记"}, {
                "v": "16",
                "n": "运动"
            }, {"v": "18", "n": "惊悚"}, {"v": "20", "n": "短片"}, {"v": "21", "n": "历史"}, {
                "v": "22",
                "n": "音乐"
            }, {"v": "23", "n": "西部"}, {"v": "24", "n": "武侠"}, {"v": "25", "n": "恐怖"}]
        }, {
            "key": "area",
            "name": "地區",
            "value": [{"v": "1", "n": "国产"}, {"v": "3", "n": "中国香港"}, {"v": "6", "n": "中国台湾"}, {
                "v": "5",
                "n": "美国"
            }, {"v": "18", "n": "韩国"}, {"v": "2", "n": "日本"}]
        }, {
            "key": "year",
            "name": "年代",
            "value": [{"v": "107", "n": "2025"}, {"v": "119", "n": "2024"}, {"v": "153", "n": "2023"}, {
                "v": "101",
                "n": "2022"
            }, {"v": "118", "n": "2021"}, {"v": "16", "n": "2020"}, {"v": "7", "n": "2019"}, {
                "v": "2",
                "n": "2018"
            }, {"v": "3", "n": "2017"}, {"v": "22", "n": "2016"}, {"v": "2015", "n": "2015以前"}]
        }, {
            "key": "sort",
            "name": "排序",
            "value": [{"v": "update", "n": "最新"}, {"v": "hot", "n": "最热"}, {"v": "rating", "n": "评分"}]
        }],
        "3": [{
            "key": "cateId",
            "name": "分类",
            "value": [{"v": "1", "n": "剧情"}, {"v": "2", "n": "爱情"}, {"v": "3", "n": "动画"}, {
                "v": "4",
                "n": "喜剧"
            }, {"v": "5", "n": "战争"}, {"v": "6", "n": "歌舞"}, {"v": "7", "n": "古装"}, {
                "v": "8",
                "n": "奇幻"
            }, {"v": "9", "n": "冒险"}, {"v": "10", "n": "动作"}, {"v": "11", "n": "科幻"}, {
                "v": "12",
                "n": "悬疑"
            }, {"v": "13", "n": "犯罪"}, {"v": "14", "n": "家庭"}, {"v": "15", "n": "传记"}, {
                "v": "16",
                "n": "运动"
            }, {"v": "18", "n": "惊悚"}, {"v": "20", "n": "短片"}, {"v": "21", "n": "历史"}, {
                "v": "22",
                "n": "音乐"
            }, {"v": "23", "n": "西部"}, {"v": "24", "n": "武侠"}, {"v": "25", "n": "恐怖"}]
        }, {
            "key": "area",
            "name": "地區",
            "value": [{"v": "1", "n": "国产"}, {"v": "3", "n": "中国香港"}, {"v": "6", "n": "中国台湾"}, {
                "v": "5",
                "n": "美国"
            }, {"v": "18", "n": "韩国"}, {"v": "2", "n": "日本"}]
        }, {
            "key": "year",
            "name": "年代",
            "value": [{"v": "107", "n": "2025"}, {"v": "119", "n": "2024"}, {"v": "153", "n": "2023"}, {
                "v": "101",
                "n": "2022"
            }, {"v": "118", "n": "2021"}, {"v": "16", "n": "2020"}, {"v": "7", "n": "2019"}, {
                "v": "2",
                "n": "2018"
            }, {"v": "3", "n": "2017"}, {"v": "22", "n": "2016"}, {"v": "2015", "n": "2015以前"}]
        }, {
            "key": "sort",
            "name": "排序",
            "value": [{"v": "update", "n": "最新"}, {"v": "hot", "n": "最热"}, {"v": "rating", "n": "评分"}]
        }],
        "4": [{
            "key": "cateId",
            "name": "分类",
            "value": [{"v": "1", "n": "剧情"}, {"v": "2", "n": "爱情"}, {"v": "3", "n": "动画"}, {
                "v": "4",
                "n": "喜剧"
            }, {"v": "5", "n": "战争"}, {"v": "6", "n": "歌舞"}, {"v": "7", "n": "古装"}, {
                "v": "8",
                "n": "奇幻"
            }, {"v": "9", "n": "冒险"}, {"v": "10", "n": "动作"}, {"v": "11", "n": "科幻"}, {
                "v": "12",
                "n": "悬疑"
            }, {"v": "13", "n": "犯罪"}, {"v": "14", "n": "家庭"}, {"v": "15", "n": "传记"}, {
                "v": "16",
                "n": "运动"
            }, {"v": "18", "n": "惊悚"}, {"v": "20", "n": "短片"}, {"v": "21", "n": "历史"}, {
                "v": "22",
                "n": "音乐"
            }, {"v": "23", "n": "西部"}, {"v": "24", "n": "武侠"}, {"v": "25", "n": "恐怖"}]
        }, {
            "key": "area",
            "name": "地區",
            "value": [{"v": "1", "n": "国产"}, {"v": "3", "n": "中国香港"}, {"v": "6", "n": "中国台湾"}, {
                "v": "5",
                "n": "美国"
            }, {"v": "18", "n": "韩国"}, {"v": "2", "n": "日本"}]
        }, {
            "key": "year",
            "name": "年代",
            "value": [{"v": "107", "n": "2025"}, {"v": "119", "n": "2024"}, {"v": "153", "n": "2023"}, {
                "v": "101",
                "n": "2022"
            }, {"v": "118", "n": "2021"}, {"v": "16", "n": "2020"}, {"v": "7", "n": "2019"}, {
                "v": "2",
                "n": "2018"
            }, {"v": "3", "n": "2017"}, {"v": "22", "n": "2016"}, {"v": "2015", "n": "2015以前"}]
        }, {
            "key": "sort",
            "name": "排序",
            "value": [{"v": "update", "n": "最新"}, {"v": "hot", "n": "最热"}, {"v": "rating", "n": "评分"}]
        }]
    };
    return JSON.stringify({
        class: classes,
        filters: filterObj,
    });
}

//主页推荐
async function homeVod() {
    let html = await req(`${host}/api/slide/list?pos_id=88`, {headers: {'User-Agent': UA, 'Referer': host}});
    let res = JSON.parse(html.content);

    let videos = res.data.map(item => ({
        vod_id: item.jump_id,
        vod_name: item.title,
        vod_pic: `${imghost}${item.thumbnail}`,
        vod_remarks: "",
        style: {"type": "rect", "ratio": 1.33}
    }))

    return JSON.stringify({
        list: videos,
    });
}

//分类
async function category(tid, pg, filter, extend) {

    let html = await req(`${host}/api/crumb/list?fcate_pid=${tid}&category_id=&area=${extend.area ? extend.area : ''}&year=${extend.year ? extend.year : ''}&type=${extend.cateId ? extend.cateId : ''}&sort=${extend.sort ? extend.sort : ''}&page=${pg}`, {
        headers: {
            'User-Agent': UA,
            'Referer': host
        }
    });
    let res = JSON.parse(html.content);

    let videos = res.data.map(item => ({
        vod_id: item.id,
        vod_name: item.title,
        vod_pic: `${imghost}${item.path}`,
        vod_remarks: item.mask,
        vod_year: ""
    }))

    return JSON.stringify({
        page: pg,
        pagecount: 99999,
        limit: 15,
        total: 99999,
        list: videos
    });
}

//详情
async function detail(id) {
    let html = await req(`${host}/api/video/detailv2?id=${id}`, {headers: {'User-Agent': UA, 'Referer': host}});

    let res = JSON.parse(html.content).data;
    let play_from = res.source_list_source.map(item => item.name).join('$$$').replace(/常规线路/g, '边下边播');
    let play_url = res.source_list_source.map(play =>
        play.source_list.map(({source_name, url}) => `${source_name}$${url}`).join('#')
    ).join('$$$');

    var vod = [{
        "type_name": '',
        "vod_year": res.year,
        "vod_area": res.area,
        "vod_remarks": res.mask,
        "vod_content": res.description,
        "vod_play_from": play_from,
        "vod_play_url": play_url
    }];

    return JSON.stringify({
        list: vod
    });
}


//播放
async function play(flag, id, flags) {
    if (id.indexOf(".m3u8") > -1) {
        return JSON.stringify({
            parse: 0,
            url: id
        });
    } else {
        return JSON.stringify({
            parse: 0,
            url: `tvbox-xg:${id}`
        });
    }
}

//搜索
async function search(wd, quick) {
    let html = await req(`${host}/api/v2/search/videoV2?key=${wd}&category_id=88&page=1&pageSize=20`, {
        headers: {
            'User-Agent': UA,
            'Referer': host
        }
    });
    let res = JSON.parse(html.content);

    let videos = res.data.map(item => ({
        vod_id: item.id,
        vod_name: item.title,
        vod_pic: `${imghost}${item.thumbnail}`,
        vod_remarks: item.mask,
        vod_year: ""
    }))

    return JSON.stringify({
        limit: 20,
        list: videos
    });
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        detail: detail,
        play: play,
        search: search
    };
}
