
var rule = {
    author: 'EylinSir修复版',
    title: '泥视频',
    类型: '影视',
    host: 'https://www.nivod.vip/',
    headers: {
        'User-Agent': 'MOBILE_UA'
    },
    编码: 'utf-8',
    timeout: 5000,
    homeUrl: '/',
    url: 'https://www.nivod.vip/k/fyfilter/',
    filter_url: '{{fl.cateId}}-{{fl.area}}-------fypage---{{fl.year}}',
    detailUrl: 'https://www.nivod.vip/nivod/fyid/',
    searchUrl: '/index.php/ajax/suggest?mid=1&wd=**&page=fypage&limit=30',
    搜索: 'json:list;name;pic;en;id',
    searchable: 1,
    quickSearch: 1,
    filterable: 1,
    limit: 10,
    double: false,
    class_name: '电影&电视剧&综艺&动漫',
    class_url: '1&2&3&4',

    filter_def: {
        1: { cateId: '1' },
        2: { cateId: '2' },
        3: { cateId: '3' },
        4: { cateId: '4' }
    },
    
    推荐: 'a:has(.lazyload);a&&title;.lazyload&&data-original;.module-item-note&&Text;a&&href',
    一级: 'a:has(.module-item-pic);a&&title;.lazyload&&data-original;.module-item-note&&Text;a&&href',

    二级: {
        title: 'h1&&Text',
        img: '.module-item-pic&&img&&data-src',
        desc: ';;.module-info-tag-link:eq(0)&&Text;.module-info-tag-link:eq(1)&&Text;.module-info-tag-link:eq(2)&&Text;.module-info-item:contains(集数)&&Text',
        content: '.module-info-introduction-content&&Text',
        tabs: '#y-playList&&span',
        lists: '.module-play-list:eq(#id)&&a'
    },

    sniffer: 0,
    isVideo: 'http((?!http).){12,}?\\.(m3u8|mp4|flv|avi|mkv|wmv|mpg|mpeg|mov|ts|3gp|rm|rmvb|asf|m4a|mp3|wma)',

    play_parse: true,
    lazy: `js:
try {
    let html = request(input);
    
    // 尝试多种匹配方式
    let match = null;
    let patterns = [
        /var player_.*?=\s*(\{.*?\})\s*</,
        /player_.*?=\s*(\{.*?\})\s*</,
        /var config\s*=\s*(\{.*?\})\s*</,
        /player_config\s*=\s*(\{.*?\})\s*</
    ];
    
    for (let pattern of patterns) {
        match = html.match(pattern);
        if (match && match[1]) {
            break;
        }
    }
    
    if (match && match[1]) {
        let kcode = JSON.parse(match[1]);
        let kurl = kcode.url;
        
        if (kcode.encrypt == '1') {
            kurl = unescape(kurl);
        } else if (kcode.encrypt == '2') {
            kurl = unescape(base64Decode(kurl));
        }
        
        if (kurl && /\.(m3u8|mp4|flv|avi|mkv)/.test(kurl)) {
            return {
                parse: 0,
                jx: 0,
                url: kurl,
                headers: {
                    'User-Agent': 'MOBILE_UA',
                    'Referer': 'https://www.nivod.vip/'
                }
            };
        }
    }
    
    // 如果上述方法失败，尝试直接提取iframe
    let iframeMatch = html.match(/<iframe[^>]*src=['"]([^'"]+)['"]/);
    if (iframeMatch && iframeMatch[1]) {
        return {
            parse: 1,
            jx: 0,
            url: iframeMatch[1]
        };
    }
    
} catch (e) {
    console.log('解析错误:', e.message);
}

// 默认返回
return {
    parse: 1,
    jx: 0,
    url: input
};
`,

    filter: {
        "1": [{
            "key": "cateId",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "1"},
                {"n": "动作片", "v": "6"},
                {"n": "喜剧片", "v": "7"},
                {"n": "爱情片", "v": "8"},
                {"n": "科幻片", "v": "9"},
                {"n": "奇幻片", "v": "10"},
                {"n": "恐怖片", "v": "11"},
                {"n": "剧情片", "v": "12"},
                {"n": "战争片", "v": "20"},
                {"n": "纪录片", "v": "21"},
                {"n": "动画片", "v": "26"},
                {"n": "悬疑片", "v": "22"},
                {"n": "冒险片", "v": "23"},
                {"n": "犯罪片", "v": "24"},
                {"n": "惊悚片", "v": "45"},
                {"n": "歌舞片", "v": "46"},
                {"n": "灾难片", "v": "47"},
                {"n": "网络片", "v": "48"}
            ]
        }, {
            "key": "area",
            "name": "地区",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "大陆", "v": "大陆"},
                {"n": "香港", "v": "香港"},
                {"n": "台湾", "v": "台湾"},
                {"n": "美国", "v": "美国"},
                {"n": "欧美", "v": "欧美"},
                {"n": "日本", "v": "日本"},
                {"n": "韩国", "v": "韩国"},
                {"n": "泰国", "v": "泰国"},
                {"n": "其他", "v": "其他"}
            ]
        }, {
            "key": "year",
            "name": "年份",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"},
                {"n": "2023", "v": "2023"},
                {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"},
                {"n": "2020", "v": "2020"},
                {"n": "2019", "v": "2019"},
                {"n": "2018", "v": "2018"},
                {"n": "2017", "v": "2017"},
                {"n": "2016", "v": "2016"},
                {"n": "2015", "v": "2015"},
                {"n": "2014", "v": "2014"},
                {"n": "2013", "v": "2013"},
                {"n": "2012", "v": "2012"}
            ]
        }],
        "2": [{
            "key": "cateId",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "2"},
                {"n": "国产剧", "v": "13"},
                {"n": "港台剧", "v": "14"},
                {"n": "日剧", "v": "15"},
                {"n": "韩剧", "v": "33"},
                {"n": "欧美剧", "v": "16"},
                {"n": "泰剧", "v": "34"},
                {"n": "新马剧", "v": "35"},
                {"n": "其他剧", "v": "25"}
            ]
        }, {
            "key": "area",
            "name": "地区",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "内地", "v": "内地"},
                {"n": "韩国", "v": "韩国"},
                {"n": "香港", "v": "香港"},
                {"n": "台湾", "v": "台湾"},
                {"n": "日本", "v": "日本"},
                {"n": "美国", "v": "美国"},
                {"n": "泰国", "v": "泰国"},
                {"n": "英国", "v": "英国"},
                {"n": "新加坡", "v": "Singapore"},
                {"n": "其他", "v": "其他"}
            ]
        }, {
            "key": "year",
            "name": "年份",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"},
                {"n": "2023", "v": "2023"},
                {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"},
                {"n": "2020", "v": "2020"},
                {"n": "2019", "v": "2019"},
                {"n": "2018", "v": "2018"},
                {"n": "2017", "v": "2017"},
                {"n": "2016", "v": "2016"},
                {"n": "2015", "v": "2015"},
                {"n": "2014", "v": "2014"},
                {"n": "2013", "v": "2013"},
                {"n": "2012", "v": "2012"}
            ]
        }],
        "3": [{
            "key": "cateId",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "3"},
                {"n": "内地综艺", "v": "27"},
                {"n": "港台综艺", "v": "28"},
                {"n": "日本综艺", "v": "29"},
                {"n": "韩国综艺", "v": "36"},
                {"n": "欧美综艺", "v": "30"},
                {"n": "新马泰综艺", "v": "37"},
                {"n": "其他综艺", "v": "38"}
            ]
        }, {
            "key": "area",
            "name": "地区",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "内地", "v": "内地"},
                {"n": "港台", "v": "港台"},
                {"n": "日韩", "v": "日韩"},
                {"n": "欧美", "v": "欧美"}
            ]
        }, {
            "key": "year",
            "name": "年份",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"},
                {"n": "2023", "v": "2023"},
                {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"},
                {"n": "2020", "v": "2020"},
                {"n": "2019", "v": "2019"},
                {"n": "2018", "v": "2018"},
                {"n": "2017", "v": "2017"},
                {"n": "2016", "v": "2016"},
                {"n": "2015", "v": "2015"},
                {"n": "2014", "v": "2014"},
                {"n": "2013", "v": "2013"},
                {"n": "2012", "v": "2012"}
            ]
        }],
        "4": [{
            "key": "cateId",
            "name": "类型",
            "value": [
                {"n": "全部", "v": "4"},
                {"n": "国产动漫", "v": "31"},
                {"n": "日本动漫", "v": "32"},
                {"n": "韩国动漫", "v": "39"},
                {"n": "港台动漫", "v": "40"},
                {"n": "新马泰动漫", "v": "41"},
                {"n": "欧美动漫", "v": "42"},
                {"n": "其他动漫", "v": "43"}
            ]
        }, {
            "key": "area",
            "name": "地区",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "国产", "v": "国产"},
                {"n": "日本", "v": "日本"},
                {"n": "欧美", "v": "欧美"},
                {"n": "其他", "v": "其他"}
            ]
        }, {
            "key": "year",
            "name": "年份",
            "value": [
                {"n": "全部", "v": ""},
                {"n": "2025", "v": "2025"},
                {"n": "2024", "v": "2024"},
                {"n": "2023", "v": "2023"},
                {"n": "2022", "v": "2022"},
                {"n": "2021", "v": "2021"},
                {"n": "2020", "v": "2020"},
                {"n": "2019", "v": "2019"},
                {"n": "2018", "v": "2018"},
                {"n": "2017", "v": "2017"},
                {"n": "2016", "v": "2016"},
                {"n": "2015", "v": "2015"},
                {"n": "2014", "v": "2014"},
                {"n": "2013", "v": "2013"},
                {"n": "2012", "v": "2012"}
            ]
        }]
    }
}