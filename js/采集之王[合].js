/**
 * 强烈推荐静态分类。可以加快速度!!!
 * 传参 ?type=url&params=../json/采集.json
 * 传参 ?type=url&params=../json/采集静态.json
 * [{"name":"暴风资源","url":"https://bfzyapi.com","parse_url":""},{"name":"飞刀资源","url":"http://www.feidaozy.com","parse_url":""},{"name":"黑木耳资源","url":"https://www.heimuer.tv","parse_url":""}]
 */
var rule = {
    title: '采集之王[合]',
    author: '道长',
    version: '20240621 beta2',
    host: '',
    homeTid: '', // 首页推荐。一般填写第一个资源站的想要的推荐分类的id.可以空
    homeUrl: '/api.php/provide/vod/?ac=detail&t={{rule.homeTid}}',
    detailUrl: '/api.php/provide/vod/?ac=detail&ids=fyid',
    searchUrl: '/api.php/provide/vod/?wd=**&pg=fypage',
    classUrl: '/api.php/provide/vod/',
    url: '/api.php/provide/vod/?ac=detail&pg=fypage&t=fyfilter',
    filter_url: '{{fl.类型}}',
    headers: {'User-Agent': 'MOBILE_UA'},
    timeout: 5000, // class_name: '电影&电视剧&综艺&动漫',
    limit: 20,
    search_limit: 5, // 搜索限制取前5个，可以注释掉，就不限制搜索
    searchable: 1,//是否启用全局搜索,
    quickSearch: 0,//是否启用快速搜索,
    filterable: 1,//是否启用分类筛选,
    play_parse: true,
    parse_url: '', // 这个参数暂时不起作用。聚合类的每个资源应该有自己独立的解析口
    // params: 'http://127.0.0.1:5707/files/json/%E9%87%87%E9%9B%86.json',
    // params: 'http://127.0.0.1:5707/files/json/采集静态.json',
    预处理: $js.toString(() => {
        function getClasses(homeObj) {
            let classes = [];
            if (homeObj.class_name && homeObj.class_url) {
                let names = homeObj.class_name.split('&');
                let urls = homeObj.class_url.split('&');
                let cnt = Math.min(names.length, urls.length);
                for (let i = 0; i < cnt; i++) {
                    classes.push({
                        'type_id': urls[i],
                        'type_name': names[i]
                    });
                }
            }
            return classes
        }

        let _url = rule.params;
        if (_url && typeof (_url) === 'string' && /^(http|file)/.test(_url)) {
            let html = request(_url);
            let json = JSON.parse(html);
            let _classes = [];
            rule.filter = {};
            rule.filter_def = {};
            json.forEach(it => {
                let _obj = {
                    type_name: it.name,
                    type_id: it.url,
                    parse_url: it.parse_url || '',
                    cate_exclude: it.cate_exclude || '',
                    // class_name: it.class_name || '',
                    // class_url: it.class_url || '',
                };
                _classes.push(_obj);
                try {
                    let json1 = [];
                    if (it.class_name && it.class_url) {
                        json1 = getClasses(it);
                    } else {
                        json1 = JSON.parse(request(urljoin(_obj.type_id, rule.classUrl))).class;
                    }
                    if (_obj.cate_exclude) {
                        json1 = json1.filter(cl => !new RegExp(_obj.cate_exclude, 'i').test(cl.type_name));
                    }
                    rule.filter[_obj.type_id] = [{
                        "key": "类型", "name": "类型", "value": json1.map(i => {
                            return {"n": i.type_name, 'v': i.type_id}
                        })
                    }];
                    if (json1.length > 0) {
                        rule.filter_def[it.url] = {"类型": json1[0].type_id};
                    }
                } catch (e) {
                    rule.filter[it.url] = [{"key": "类型", "name": "类型", "value": [{"n": "全部", "v": ""}]}];
                }
            });
            rule.classes = _classes;
        }
    }),
    // class_parse: $js.toString(() => {
    //     let _url = rule.params;
    //     if (_url && typeof (_url) === 'string' && _url.startsWith('http')) {
    //         let html = request(_url);
    //         let json = JSON.parse(html);
    //         let _classes = [];
    //         homeObj.filter = {};
    //         rule.filter_def = {};
    //         json.forEach(it => {
    //             let _obj = {
    //                 type_name: it.name,
    //                 type_id: it.url,
    //                 parse_url: it.parse_url || '',
    //                 cate_exclude: it.cate_exclude || '',
    //             };
    //             _classes.push(_obj);
    //             try {
    //                 let json1 = JSON.parse(request(urljoin(_obj.type_id, rule.classUrl))).class;
    //                 if (_obj.cate_exclude) {
    //                     json1 = json1.filter(cl => !new RegExp(_obj.cate_exclude, 'i').test(cl.type_name));
    //                 }
    //                 homeObj.filter[_obj.type_id] = [{
    //                     "key": "类型", "name": "类型", "value": json1.map(i => {
    //                         return {"n": i.type_name, 'v': i.type_id}
    //                     })
    //                 }];
    //                 if (json1.length > 0) {
    //                     rule.filter_def[it.url] = {"类型": json1[0].type_id};
    //                 }
    //             } catch (e) {
    //                 homeObj.filter[it.url] = [{"key": "类型", "name": "类型", "value": [{"n": "全部", "v": ""}]}];
    //             }
    //         });
    //         rule.classes = _classes;
    //         input = _classes;
    //     }
    // }),
    class_parse: $js.toString(() => {
        input = rule.classes;
    }),
    推荐: $js.toString(() => {
        VODS = [];
        if (rule.classes) {
            let _url = urljoin(rule.classes[0].type_id, input);
            try {
                let html = request(_url);
                let json = JSON.parse(html);
                VODS = json.list;
                VODS.forEach(it => {
                    it.vod_id = rule.classes[0].type_id + '$' + it.vod_id
                });
            } catch (e) {
            }
        }
    }),
    一级: $js.toString(() => {
        VODS = [];
        if (rule.classes) {
            // log(input);
            let _url = urljoin(MY_CATE, input);
            let html = request(_url);
            let json = JSON.parse(html);
            VODS = json.list;
            VODS.forEach(it => {
                it.vod_id = MY_CATE + '$' + it.vod_id
            });
        }
    }),
    // 一级: 'json:list;vod_name;vod_pic;vod_remarks;vod_id;vod_play_from',
    二级: $js.toString(() => {
        VOD = [];
        if (rule.classes) {
            let _url = urljoin(fyclass, input);
            let html = request(_url);
            let json = JSON.parse(html);
            let data = json.list;
            VOD = data[0];
        }
    }),
    搜索: $js.toString(() => {
        VODS = [];
        if (rule.classes) {
            if (rule.search_limit) {
                rule.classes = rule.classes.slice(0, rule.search_limit);
            }
            rule.classes.forEach(it => {
                let _url = urljoin(it.type_id, input);
                // log(_url);
                try {
                    let html = request(_url);
                    let json = JSON.parse(html);
                    let data = json.list;
                    data.forEach(i => {
                        i.vod_id = it.type_id + '$' + i.vod_id;
                        i.vod_remarks = i.vod_remarks + '|' + it.type_name;
                    });
                    VODS = VODS.concat(data);
                } catch (e) {
                    log(`请求:${it.type_id}发生错误:${e.message}`)
                }

            });
        }
    }),
    lazy: $js.toString(() => {
        // lazy想办法用对应的parse_url，但是有难度，暂未实现
        if (/\.(m3u8|mp4)/.test(input)) {
            input = {parse: 0, url: input}
        } else {
            if (rule.parse_url.startsWith('json:')) {
                let purl = rule.parse_url.replace('json:', '') + input;
                let html = request(purl);
                input = {parse: 0, url: JSON.parse(html).url}
            } else {
                input = rule.parse_url + input;
            }
        }
    }),
}