/**
 * 荐片 新式 JS0 接口源
 * 适配 FongMi TVBox 最新规范
 */

let host = 'https://api.ztcgi.com';
let UA = 'Mozilla/5.0 (Linux; Android 9; V2196A Build/PQ3A.190705.08211809; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36;webank/h5face;webank/1.0;netType:NETWORK_WIFI;appVersion:416;packageName:com.jp3.xg3';
let imghost = '';

/**
 * 初始化配置
 */
async function init(cfg) {
    try {
        let res = await req(`${host}/api/appAuthConfig`, { headers: { 'User-Agent': UA } });
        let config = JSON.parse(res.content);
        imghost = `https://${config.data.imgDomain}`;
    } catch (e) {
        imghost = 'https://img.jianpian.com';
    }
}

/**
 * 首页分类与筛选
 */
async function home(filter) {
    let classes = [
        {type_id: '1', type_name: '电影'},
        {type_id: '2', type_name: '电视剧'},
        {type_id: '3', type_name: '动漫'},
        {type_id: '4', type_name: '综艺'}
    ];

    // 筛选数据模板
    const filterItem = [
        {"key": "cateId", "name": "分类", "value": [{"v": "1", "n": "剧情"}, {"v": "2", "n": "爱情"}, {"v": "3", "n": "动画"}, {"v": "4", "n": "喜剧"}, {"v": "5", "n": "战争"}, {"v": "6", "n": "歌舞"}, {"v": "7", "n": "古装"}, {"v": "8", "n": "奇幻"}, {"v": "9", "n": "冒险"}, {"v": "10", "n": "动作"}, {"v": "11", "n": "科幻"}, {"v": "12", "n": "悬疑"}, {"v": "13", "n": "犯罪"}, {"v": "14", "n": "家庭"}, {"v": "15", "n": "传记"}, {"v": "16", "n": "运动"}, {"v": "18", "n": "惊悚"}, {"v": "20", "n": "短片"}, {"v": "21", "n": "历史"}, {"v": "22", "n": "音乐"}, {"v": "23", "n": "西部"}, {"v": "24", "n": "武侠"}, {"v": "25", "n": "恐怖"}]},
        {"key": "area", "name": "地區", "value": [{"v": "1", "n": "国产"}, {"v": "3", "n": "中国香港"}, {"v": "6", "n": "中国台湾"}, {"v": "5", "n": "美国"}, {"v": "18", "n": "韩国"}, {"v": "2", "n": "日本"}]},
        {"key": "year", "name": "年代", "value": [{"v": "107", "n": "2025"}, {"v": "119", "n": "2024"}, {"v": "153", "n": "2023"}, {"v": "101", "n": "2022"}, {"v": "118", "n": "2021"}, {"v": "16", "n": "2020"}, {"v": "7", "n": "2019"}, {"v": "22", "n": "2016"}, {"v": "2015", "n": "2015以前"}]},
        {"key": "sort", "name": "排序", "value": [{"v": "update", "n": "最新"}, {"v": "hot", "n": "最热"}, {"v": "rating", "n": "评分"}]}
    ];

    let filterObj = {"1": filterItem, "2": filterItem, "3": filterItem, "4": filterItem};

    return JSON.stringify({
        class: classes,
        filters: filterObj
    });
}

/**
 * 首页推荐
 */
async function homeVod() {
    let html = await req(`${host}/api/slide/list?pos_id=88`, { headers: { 'User-Agent': UA, 'Referer': host } });
    let res = JSON.parse(html.content);
    let videos = res.data.map(item => ({
        vod_id: item.jump_id,
        vod_name: item.title,
        vod_pic: item.thumbnail.includes('http') ? item.thumbnail : `${imghost}${item.thumbnail}`,
        vod_remarks: ""
    }));
    return JSON.stringify({ list: videos });
}

/**
 * 分类列表
 */
async function category(tid, pg, filter, extend) {
    let url = `${host}/api/crumb/list?fcate_pid=${tid}&category_id=&area=${extend.area || ''}&year=${extend.year || ''}&type=${extend.cateId || ''}&sort=${extend.sort || ''}&page=${pg}`;
    let html = await req(url, { headers: { 'User-Agent': UA, 'Referer': host } });
    let res = JSON.parse(html.content);
    let videos = res.data.map(item => ({
        vod_id: item.id,
        vod_name: item.title,
        vod_pic: item.path.includes('http') ? item.path : `${imghost}${item.path}`,
        vod_remarks: item.mask
    }));
    return JSON.stringify({
        page: pg,
        list: videos
    });
}

/**
 * 详情页
 */
async function detail(id) {
    let html = await req(`${host}/api/video/detailv2?id=${id}`, { headers: { 'User-Agent': UA, 'Referer': host } });
    let data = JSON.parse(html.content).data;
    
    // 线路处理：将“常规线路”显示为“边下边播”
    let play_from = data.source_list_source.map(item => item.name).join('$$$').replace(/常规线路/g, '边下边播');
    let play_url = data.source_list_source.map(play =>
        play.source_list.map(({source_name, url}) => `${source_name}$${url}`).join('#')
    ).join('$$$');

    let vod = {
        vod_id: data.id,
        vod_name: data.title,
        vod_year: data.year,
        vod_area: data.area,
        vod_remarks: data.mask,
        vod_content: data.description,
        vod_play_from: play_from,
        vod_play_url: play_url,
        vod_pic: data.thumbnail.includes('http') ? data.thumbnail : `${imghost}${data.thumbnail}`
    };

    return JSON.stringify({ list: [vod] });
}

/**
 * 搜索功能
 */
async function search(wd, quick) {
    let url = `${host}/api/v2/search/videoV2?key=${encodeURIComponent(wd)}&category_id=88&page=1&pageSize=20`;
    let html = await req(url, { headers: { 'User-Agent': UA, 'Referer': host } });
    let res = JSON.parse(html.content);
    let videos = res.data.map(item => ({
        vod_id: item.id,
        vod_name: item.title,
        vod_pic: item.thumbnail.includes('http') ? item.thumbnail : `${imghost}${item.thumbnail}`,
        vod_remarks: item.mask
    }));
    return JSON.stringify({ list: videos });
}

/**
 * 播放解析
 */
async function play(flag, id, flags) {
    let playUrl = id;
    // 判断是否需要添加专用协议前缀
    if (!id.includes(".m3u8") && !id.includes(".mp4")) {
        playUrl = `tvbox-xg:${id}`;
    }
    return JSON.stringify({
        parse: 0,
        url: playUrl
    });
}

// 导出标准接口对象
export default {
    init,
    home,
    homeVod,
    category,
    detail,
    search,
    play
};
