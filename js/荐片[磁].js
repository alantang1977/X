var rule = {
    title: '荐片[优]',
    //host: 'https://api.ubj83.com',
    host: 'https://api.ztcgi.com',
    homeUrl: '/api/dyTag/hand_data?category_id=88',
    url: '/api/crumb/list?page=fypage&type=0&limit=24&fyfilter',
    class_name: '电影&电视剧&动漫&短剧&综艺',
    class_url: '1&2&3&67&4',
    detailUrl: '/api/video/detailv2?id=fyid',
    searchUrl: '/api/v2/search/videoV2?key=**&page=fypage',
    searchable: 2,
    quickSearch: 0,
    filterable: 1,
    filter: {
      "1":[{"key":"cateId","name":"分类","value":[{"n":"全部","v":"1"},{"n":"首推","v":"5"},{"n":"动作","v":"6"},{"n":"喜剧","v":"7"},{"n":"战争","v":"8"},{"n":"恐怖","v":"9"},{"n":"剧情","v":"10"},{"n":"爱情","v":"11"},{"n":"科幻","v":"12"},{"n":"动画","v":"13"}]},{"key":"area","name":"地區","value":[{"n":"全部","v":"0"},{"n":"国产","v":"1"},{"n":"中国香港","v":"3"},{"n":"中国台湾","v":"6"},{"n":"美国","v":"5"},{"n":"韩国","v":"18"},{"n":"日本","v":"2"}]},{"key":"year","name":"年代","value":[{"n":"全部","v":"0"},{"n":"2025","v":"107"},{"n":"2024","v":"119"},{"n":"2023","v":"153"},{"n":"2022","v":"101"},{"n":"2021","v":"118"},{"n":"2020","v":"16"},{"n":"2019","v":"7"},{"n":"2018","v":"2"},{"n":"2017","v":"3"},{"n":"2016","v":"22"}]},{"key":"sort","name":"排序","value":[{"n":"热门","v":"hot"},{"n":"评分","v":"rating"},{"n":"更新","v":"update"}]}],
      "2":[{"key":"cateId","name":"分类","value":[{"n":"全部","v":"2"},{"n":"首推","v":"14"},{"n":"国产","v":"15"},{"n":"港台","v":"16"},{"n":"日韩","v":"17"},{"n":"海外","v":"18"}]},{"key":"area","name":"地區","value":[{"n":"全部","v":"0"},{"n":"国产","v":"1"},{"n":"中国香港","v":"3"},{"n":"中国台湾","v":"6"},{"n":"美国","v":"5"},{"n":"韩国","v":"18"},{"n":"日本","v":"2"}]},{"key":"year","name":"年代","value":[{"n":"全部","v":"0"},{"n":"2025","v":"107"},{"n":"2024","v":"119"},{"n":"2023","v":"153"},{"n":"2022","v":"101"},{"n":"2021","v":"118"},{"n":"2020","v":"16"},{"n":"2019","v":"7"},{"n":"2018","v":"2"},{"n":"2017","v":"3"},{"n":"2016","v":"22"}]},{"key":"sort","name":"排序","value":[{"n":"热门","v":"hot"},{"n":"评分","v":"rating"},{"n":"更新","v":"update"}]}],
      "3":[{"key":"cateId","name":"分类","value":[{"n":"全部","v":"3"},{"n":"首推","v":"19"},{"n":"海外","v":"20"},{"n":"日本","v":"21"},{"n":"国产","v":"22"}]},{"key":"area","name":"地區","value":[{"n":"全部","v":"0"},{"n":"国产","v":"1"},{"n":"中国香港","v":"3"},{"n":"中国台湾","v":"6"},{"n":"美国","v":"5"},{"n":"韩国","v":"18"},{"n":"日本","v":"2"}]},{"key":"year","name":"年代","value":[{"n":"全部","v":"0"},{"n":"2025","v":"107"},{"n":"2024","v":"119"},{"n":"2023","v":"153"},{"n":"2022","v":"101"},{"n":"2021","v":"118"},{"n":"2020","v":"16"},{"n":"2019","v":"7"},{"n":"2018","v":"2"},{"n":"2017","v":"3"},{"n":"2016","v":"22"}]},{"key":"sort","name":"排序","value":[{"n":"热门","v":"hot"},{"n":"评分","v":"rating"},{"n":"更新","v":"update"}]}],
      "4":[{"key":"cateId","name":"分类","value":[{"n":"全部","v":"4"},{"n":"首推","v":"23"},{"n":"国产","v":"24"},{"n":"海外","v":"25"},{"n":"港台","v":"26"}]},{"key":"area","name":"地區","value":[{"n":"全部","v":"0"},{"n":"国产","v":"1"},{"n":"中国香港","v":"3"},{"n":"中国台湾","v":"6"},{"n":"美国","v":"5"},{"极":"韩国","v":"18"},{"n":"日本","v":"2"}]},{"key":"year","name":"年代","value":[{"n":"全部","v":"0"},{"n":"2025","v":"107"},{"n":"2024","v":"119"},{"n":"2023","v":"153"},{"n":"2022","v":"101"},{"n":"2021","v":"118"},{"极":"2020","v":"16"},{"n":"2019","v":"7"},{"n":"2018","极":"2"},{"n":"2017","v":"3"},{"n":"2016","v":"22"}]},{"key":"sort","name":"排序","value":[{"n":"热门","v":"hot"},{"n":"评分","v":"rating"},{"n":"更新","v":"update"}]}],
      "67":[{"key":"cate极","name":"分类","value":[{"n":"全部","v":"67"},{"n":"言情","v":"70"},{"n":"爱情","v":"71"},{"n":"战神","v":"72"},{"n":"古代","v":"73"},{"n":"萌娃","v":"74"},{"n":"神医","v":"75"},{"n":"玄幻","v":"76"},{"n":"重生","v":"77"},{"n":"激情","v":"79"},{"n":"时尚","v":"82"},{"n":"剧情演绎","v":"83"},{"n":"影视","v":"84"},{"n":"人文社科","v":"85"},{"n":"二次元","v":"86"},{"n":"明星八卦","v":"87"},{"n":"随拍","v":"88"},{"n":"个人管理","v":"89"},{"n":"音乐","v":"90"},{"n":"汽车","v":"91"},{"n":"休闲","v":"92"},{"n":"校园教育","极":"93"},{"n":"游戏","v":"94"},{"n":"科普","v":"95"},{"n":"科技","v":"96"},{"n":"时政社会","v":"97"},{"n":"萌宠","v":"98"},{"n":"体育","v":"99"},{"n":"穿越","v":"80"},{"n":"","v":"81"},{"n":"闪婚","v":"112"}]},{"key":"sort","name":"排序","value":[{"n":"全部","v":""},{"n":"最新","v":"update"},{"n":"最热","v":"hot"}]}]
    },
    filter_url: 'area={{fl.area or "0"}}&sort={{fl.sort or "update"}}&year={{fl.year or "0"}}&category_id={{fl.cateId}}',
    filter_def: {1: {cateId: '1'},2: {cateId: '2'},3: {cateId: '3'},4: {cateId: '4'},67: {cateId: '67'}},
    /*headers: {
        'User-Agent': 'jianpian-android/350',
        'JPAUTH': 'y261ow7kF2dtzlxh1GS9EB8nbTxNmaK/QQIAjctlKiEv'
    },*/
    headers: {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 9; V2196A Build/PQ3A.190705.08211809; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36;webank/h5face;webank/1.0;netType:NETWORK_WIFI;appVersion:416;packageName:com.jp3.xg3',
    },
    timeout: 5000,
    limit: 8,
    play_parse: true,
    play_json: [{
        re: '*',
        json: {
            parse: 0,
            jx: 0
        }
    }],
    lazy: '',
    预处理: function() {
        this.imghost = 'https://img1.vbwus.com';        
        try {
            const configUrl = this.host + '/api/appAuthConfig';
            const response = request(configUrl, {headers: this.headers});
            const res = JSON.parse(response);
            if (res && res.data && res.data.imgDomain) {
                this.imghost = 'https://' + res.data.imgDomain;
            }
        } catch (e) {
            console.log('获取动态图片域名失败，使用默认域名');
        }
    },
    推荐: $js.toString(() => {
        rule.预处理();        
        const data = JSON.parse(request(input)).data["20"];
        const d = data.map(item => ({
            title: item.title,
            img: rule.imghost + item.path,
            desc: (item.mask || item.playlist?.title) + ' ⭐' + item.score,
            url: item.id
        }));
        setResult(d);
    }),
    一级: $js.toString(() => {
        rule.预处理();        
        const tid = String(cateObj.tid);
        let apiUrl = input;        
        if (tid === '67') {
            apiUrl = apiUrl.replace('/api/crumb/list', '/api/crumb/shortList');
        }        
        if (tid.endsWith('_clicklink')) {
            const realTid = tid.split('_')[0];
            apiUrl = `${HOST}/api/video/search?key=${realTid}&page=${MY_PAGE}`;
        }        
        const data = JSON.parse(request(apiUrl)).data;
        const d = data.map(item => {
            const isShort = tid === '67';
            const imgUrl = rule.imghost + 
                (isShort ? (item.cover_image || item.path) : (item.thumbnail || item.path));           
            return {
                title: item.title,
                img: imgUrl,
                desc: (item.mask || item.playlist?.title) + ' ⭐' + item.score,
                url: `${item.id}@${tid}` 
            };
        });        
        setResult(d);
    }),
    二级: $js.toString(() => {
        rule.预处理();        
        try {
            const [id, tid] = input.split('=')[1].split('@');
            const isShort = tid === '67';            
            const apiConfig = {
                path: isShort ? '/api/detail' : '/api/video/detailv2',
                param: isShort ? 'vid' : 'id'
            };            
            const apiUrl = `${HOST}${apiConfig.path}?${apiConfig.param}=${id}`;
            const response = request(apiUrl, {headers: rule.headers});
            const itemData = JSON.parse(response).data;            
            const vodInfo = {
                vod_id: id,
                vod_name: itemData.title,
                vod_pic: rule.imghost + (
                    isShort 
                        ? (itemData.cover_image || itemData.path || '') 
                        : (itemData.thumbnail || itemData.path || '')
                ),
                type_name: itemData.types?.map(t => t.name).join('/') || '',
                vod_year: itemData.year || '',
                vod_area: itemData.area || '',
                vod_remarks: itemData.update_cycle || '',
                vod_actor: itemData.actors?.map(a => a.name).join('/') || '',
                vod_director: itemData.directors?.map(d => d.name).join('/') || '',
                vod_content: itemData.description || ''
            };            
            let playSources = [];            
            function renamePlaySource(name) {
                return name === "常规线路" ? "边下边播线路" : name;
            }            
            if (isShort) {
                const playlist = itemData.playlist || [];
                if (playlist.length > 0) {
                    let sourceName = playlist[0]?.source_config_name || "短剧";
                    sourceName = renamePlaySource(sourceName);                    
                    const episodes = playlist.map(ep => `${ep.title}$${ep.url}`);
                    playSources.push({
                        name: sourceName,
                        urls: episodes.join('#')
                    });
                }
            } else {
                const sources = itemData.source_list_source || [];
                sources.forEach(source => {
                    let sourceName = renamePlaySource(source.name);                    
                    const episodes = source.source_list?.map(ep => 
                        `${ep.source_name || ep.weight}$${ep.url}`
                    ) || [];                    
                    if (episodes.length > 0) {
                        playSources.push({
                            name: sourceName,
                            urls: episodes.join('#')
                        });
                    }
                });
            }
            if (playSources.length > 0) {
                vodInfo.vod_play_from = playSources.map(s => s.name).join('$$$');
                vodInfo.vod_play_url = playSources.map(s => s.urls).join('$$$');
            }
            VOD = vodInfo;            
        } catch (error) {
            log(`二级详情解析失败: ${error.message}`);
            log(`请求URL: ${input}`);
        }
    }),
    搜索: $js.toString(() => {
        rule.预处理();        
        const data = JSON.parse(request(input)).data;
        const d = data.map(item => ({
            title: item.title,
            img: rule.imghost + item.thumbnail,
            desc: item.mask + ' ⭐' + item.score,
            url: item.id
        }));
        setResult(d);
    }),
}