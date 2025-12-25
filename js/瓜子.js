const crypto = require('crypto');
const CryptoJS = require('crypto-js');
const NodeRSA = require('node-rsa');
const axios = require('axios');

class Spider {
    constructor() {
        this.name = "瓜子";
        this.host = 'https://api.w32z7vtd.com';
        this.token = '1be86e8e18a9fa18b2b8d5432699dad0.ac008ed650fd087bfbecf2fda9d82e9835253ef24843e6b18fcd128b10763497bcf9d53e959f5377cde038c20ccf9d17f604c9b8bb6e61041def86729b2fc7408bd241e23c213ac57f0226ee656e2bb0a583ae0e4f3bf6c6ab6c490c9a6f0d8cdfd366aacf5d83193671a8f77cd1af1ff2e9145de92ec43ec87cf4bdc563f6e919fe32861b0e93b118ec37d8035fbb3c.59dd05c5d9a8ae726528783128218f15fe6f2c0c8145eddab112b374fcfe3d79';
        this.header = {
            'Cache-Control': 'no-cache',
            'Version': '2406025',
            'PackageName': 'com.uf076bf0c246.qe439f0d5e.m8aaf56b725a.ifeb647346f',
            'Ver': '1.9.2',
            'Referer': this.host,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'okhttp/3.12.0'
        };
        // 缓存机制
        this.cache = {};
        this.cacheTimeout = 300; // 5分钟缓存
    }

    getName() {
        return this.name;
    }

    init(extend = '') {
        // 初始化方法
    }

    homeContent(filter) {
        const result = {};
        const classes = [
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "电视剧", "type_id": "2"},
            {"type_name": "动漫", "type_id": "4"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "短剧", "type_id": "64"}
        ];
        
        result.class = classes;
        
        // 设置筛选条件
        const filters = {};
        for (const cate of classes) {
            const tid = cate.type_id;
            filters[tid] = [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": "0"},
                    {"n": "大陆", "v": "大陆"},
                    {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"},
                    {"n": "美国", "v": "美国"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "英国", "v": "英国"},
                    {"n": "法国", "v": "法国"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "印度", "v": "印度"},
                    {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": "0"},
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
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"},
                    {"n": "2008", "v": "2008"},
                    {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"},
                    {"n": "2005", "v": "2005"},
                    {"n": "更早", "v": "2004"}
                ]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新", "v": "d_id"},
                    {"n": "最热", "v": "d_hits"},
                    {"n": "推荐", "v": "d_score"}
                ]}
            ];
        }
        
        result.filters = filters;
        return result;
    }

    homeVideoContent() {
        // 首页推荐返回空列表
        return { 'list': [] };
    }

    async categoryContent(tid, pg, filter, extend) {
        const videos = [];
        try {
            const body = {
                "area": extend?.area || '0',
                "year": extend?.year || '0',
                "pageSize": "30",
                "sort": extend?.sort || 'd_id',
                "page": pg.toString(),
                "tid": tid
            };
            
            const cacheKey = `category_${tid}_${pg}_${this.hashCode(JSON.stringify(body))}`;
            const data = await this.getCachedData(cacheKey, body, '/App/IndexList/indexList');
            
            if (data && data.list) {
                for (const item of data.list) {
                    const vodContinu = item.vod_continu || 0;
                    const remarks = vodContinu === 0 ? '电影' : `更新至${vodContinu}集`;
                    
                    const video = {
                        "vod_id": `${item.vod_id || ''}/${vodContinu}`,
                        "vod_name": item.vod_name || '',
                        "vod_pic": item.vod_pic || '',
                        "vod_remarks": remarks
                    };
                    videos.push(video);
                }
            }
        } catch (e) {
            console.error(`获取分类内容失败: ${e}`);
        }
        
        return {
            'list': videos,
            'page': parseInt(pg, 10),
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        };
    }

    async detailContent(ids) {
        try {
            const vodId = ids[0].split('/')[0];
            
            // 获取视频详情
            const t = Math.floor(Date.now() / 1000).toString();
            const body1 = {
                "token_id": "1649412",
                "vod_id": vodId,
                "mobile_time": t,
                "token": this.token
            };
            const qdata = await this.getData(body1, '/App/IndexPlay/playInfo');
            
            // 获取播放列表
            const body2 = {
                "vurl_cloud_id": "2",
                "vod_d_id": vodId
            };
            const jdata = await this.getData(body2, '/App/Resource/Vurl/show');
            
            if (!qdata || !qdata.vodInfo) {
                return { 'list': [] };
            }
            
            const vod = qdata.vodInfo;
            
            // 构建视频信息
            const videoDetail = {
                "vod_id": vodId,
                "vod_name": vod.vod_name || '',
                "vod_pic": vod.vod_pic || '',
                "vod_year": vod.vod_year || '',
                "vod_area": vod.vod_area || '',
                "vod_actor": vod.vod_actor || '',
                "vod_director": vod.vod_director || '',
                "vod_content": (vod.vod_use_content || '').trim(),
                "vod_play_from": "嗷呜要吃瓜"
            };
            
            // 构建播放列表
            const playList = [];
            if (jdata && jdata.list) {
                for (let index = 0; index < jdata.list.length; index++) {
                    const item = jdata.list[index];
                    if (item.play) {
                        const n = []; // 播放源名称
                        const p = []; // 播放参数
                        
                        for (const key in item.play) {
                            if (item.play.hasOwnProperty(key)) {
                                const value = item.play[key];
                                if (value.param) {
                                    n.push(key);
                                    p.push(value.param);
                                }
                            }
                        }
                        
                        if (p.length > 0) {
                            let playName = (index + 1).toString();
                            if (jdata.list.length === 1) {
                                playName = vod.vod_name || '';
                            }
                            
                            const playUrl = `${p[p.length - 1]}||${n.join('@')}`;
                            playList.push(`${playName}$${playUrl}`);
                        }
                    }
                }
            }
            
            videoDetail.vod_play_url = playList.join('#');
            
            return { 'list': [videoDetail] };
            
        } catch (e) {
            console.error(`获取详情失败: ${e}`);
            return { 'list': [] };
        }
    }

    async searchContent(key, quick, pg = 1) {
        const videos = [];
        try {
            const body = {
                "keywords": key,
                "order_val": "1",
                "page": pg.toString()
            };
            
            // 搜索不使用缓存，确保实时性
            const startTime = Date.now();
            const data = await this.getData(body, '/App/Index/findMoreVod', false);
            const endTime = Date.now();
            
            console.log(`搜索请求耗时: ${(endTime - startTime) / 1000}秒`);
            
            if (data && data.list) {
                for (const item of data.list) {
                    const vodContinu = item.vod_continu || 0;
                    const remarks = vodContinu === 0 ? '电影' : `更新至${vodContinu}集`;
                    
                    const video = {
                        "vod_id": `${item.vod_id || ''}/${vodContinu}`,
                        "vod_name": item.vod_name || '',
                        "vod_pic": item.vod_pic || '',
                        "vod_remarks": remarks
                    };
                    videos.push(video);
                }
            }
        } catch (e) {
            console.error(`搜索失败: ${e}`);
        }
        
        return {
            'list': videos,
            'page': parseInt(pg, 10),
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        };
    }

    async playerContent(flag, id, vipFlags) {
        try {
            // 解析播放信息
            const parts = id.split('||');
            if (parts.length < 2) {
                return { "parse": 0, "playUrl": "", "url": "" };
            }
            
            const paramStr = parts[0];
            const resolutions = parts.length > 1 ? parts[1].split('@') : [];
            
            // 解析参数
            const params = {};
            for (const pair of paramStr.split('&')) {
                if (pair.includes('=')) {
                    const [key, value] = pair.split('=', 2);
                    params[key] = value;
                }
            }
            
            // 获取播放链接
            if (resolutions.length > 0) {
                // 分辨率从大到小排序
                resolutions.sort((a, b) => {
                    const numA = parseInt(a, 10) || 0;
                    const numB = parseInt(b, 10) || 0;
                    return numB - numA;
                });
                
                // 使用最大分辨率
                params.resolution = resolutions[0];
                const body = params;
                
                const startTime = Date.now();
                const data = await this.getData(body, '/App/Resource/VurlDetail/showOne', false);
                const endTime = Date.now();
                console.log(`播放链接获取耗时: ${(endTime - startTime) / 1000}秒`);
                
                if (data && data.url) {
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": data.url,
                        "header": JSON.stringify(this.header)
                    };
                }
            }
            
            return { "parse": 0, "playUrl": "", "url": "" };
            
        } catch (e) {
            console.error(`播放解析失败: ${e}`);
            return { "parse": 0, "playUrl": "", "url": "" };
        }
    }

    isVideoFormat(url) {
        const videoFormats = ['.m3u8', '.mp4', '.avi', '.mkv', '.flv', '.ts'];
        return videoFormats.some(fmt => url.toLowerCase().endsWith(fmt));
    }

    manualVideoCheck() {
        // 空实现
    }

    localProxy(params) {
        return null;
    }

    aesEncrypt(text, key, iv) {
        try {
            const keyBytes = CryptoJS.enc.Utf8.parse(key);
            const ivBytes = CryptoJS.enc.Utf8.parse(iv);
            const encrypted = CryptoJS.AES.encrypt(
                CryptoJS.enc.Utf8.parse(text),
                keyBytes,
                {
                    iv: ivBytes,
                    mode: CryptoJS.mode.CBC,
                    padding: CryptoJS.pad.Pkcs7
                }
            );
            return encrypted.ciphertext.toString().toUpperCase();
        } catch (e) {
            console.error(`AES加密失败: ${e}`);
            return "";
        }
    }

    aesDecrypt(text, key, iv) {
        try {
            const keyBytes = CryptoJS.enc.Utf8.parse(key);
            const ivBytes = CryptoJS.enc.Utf8.parse(iv);
            const encryptedHex = CryptoJS.enc.Hex.parse(text);
            const encryptedBase64 = CryptoJS.enc.Base64.stringify(encryptedHex);
            
            const decrypted = CryptoJS.AES.decrypt(
                encryptedBase64,
                keyBytes,
                {
                    iv: ivBytes,
                    mode: CryptoJS.mode.CBC,
                    padding: CryptoJS.pad.Pkcs7
                }
            );
            
            return decrypted.toString(CryptoJS.enc.Utf8);
        } catch (e) {
            console.error(`AES解密失败: ${e}`);
            return "";
        }
    }

    rsaDecrypt(encryptedData, privateKey) {
        try {
            const key = new NodeRSA(privateKey);
            key.setOptions({ encryptionScheme: 'pkcs1' });
            return key.decrypt(Buffer.from(encryptedData, 'base64'), 'utf8');
        } catch (e) {
            console.error(`RSA解密失败: ${e}`);
            return "";
        }
    }

    async getCachedData(cacheKey, data, path) {
        const currentTime = Date.now() / 1000;
        if (this.cache[cacheKey]) {
            const [cachedData, timestamp] = this.cache[cacheKey];
            if (currentTime - timestamp < this.cacheTimeout) {
                return cachedData;
            }
        }
        
        // 缓存不存在或已过期，重新获取
        const result = await this.getData(data, path);
        if (result) {
            this.cache[cacheKey] = [result, currentTime];
        }
        return result;
    }

    async getData(data, path, useCache = true) {
        try {
            // 构建缓存键
            let cacheKey = useCache ? `${path}_${this.hashCode(JSON.stringify(data))}` : null;
            
            if (useCache && cacheKey && this.cache[cacheKey]) {
                const [cachedData, timestamp] = this.cache[cacheKey];
                if (Date.now() / 1000 - timestamp < this.cacheTimeout) {
                    return cachedData;
                }
            }

            const startTime = Date.now();
            
            // AES加密请求数据
            const requestKey = this.aesEncrypt(JSON.stringify(data), 'mvXBSW7ekreItNsT', '2U3IrJL8szAKp0Fj');
            if (!requestKey) {
                return null;
            }
            
            // 生成签名
            const t = Math.floor(Date.now() / 1000).toString();
            const keys = "Qmxi5ciWXbQzkr7o+SUNiUuQxQEf8/AVyUWY4T/BGhcXBIUz4nOyHBGf9A4KbM0iKF3yp9M7WAY0rrs5PzdTAOB45plcS2zZ0wUibcXuGJ29VVGRWKGwE9zu2vLwhfgjTaaDpXo4rby+7GxXTktzJmxvneOUdYeHi+PZsThlvPI=";
            const signStr = `token_id=,token=${this.token},phone_type=1,request_key=${requestKey},app_id=1,time=${t},keys=${keys}*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br`;
            const signature = this.getMd5(signStr);
            
            // 构建请求体
            const body = new URLSearchParams();
            body.append('token', this.token);
            body.append('token_id', '');
            body.append('phone_type', '1');
            body.append('time', t);
            body.append('phone_model', 'xiaomi-22021211rc');
            body.append('keys', keys);
            body.append('request_key', requestKey);
            body.append('signature', signature);
            body.append('app_id', '1');
            body.append('ad_version', '1');
            
            // 发送请求
            const url = `${this.host}${path}`;
            const response = await axios.post(url, body.toString(), {
                headers: this.header,
                timeout: 10000
            });
            
            if (response.status !== 200) {
                console.error(`API请求失败: ${response.status}, 路径: ${path}`);
                return null;
            }
            
            const responseData = response.data;
            if (!responseData.data) {
                console.error(`API返回数据格式错误, 路径: ${path}`);
                return null;
            }
            
            const dataResponse = responseData.data;
            
            // RSA解密响应密钥
            const privateKey = `-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGAe6hKrWLi1zQmjTT1
ozbE4QdFeJGNxubxld6GrFGximxfMsMB6BpJhpcTouAqywAFppiKetUBBbXwYsYU
1wNr648XVmPmCMCy4rY8vdliFnbMUj086DU6Z+/oXBdWU3/b1G0DN3E9wULRSwcK
ZT3wj/cCI1vsCm3gj2R5SqkA9Y0CAwEAAQKBgAJH+4CxV0/zBVcLiBCHvSANm0l7
HetybTh/j2p0Y1sTXro4ALwAaCTUeqdBjWiLSo9lNwDHFyq8zX90+gNxa7c5EqcW
V9FmlVXr8VhfBzcZo1nXeNdXFT7tQ2yah/odtdcx+vRMSGJd1t/5k5bDd9wAvYdI
DblMAg+wiKKZ5KcdAkEA1cCakEN4NexkF5tHPRrR6XOY/XHfkqXxEhMqmNbB9U34
saTJnLWIHC8IXys6Qmzz30TtzCjuOqKRRy+FMM4TdwJBAJQZFPjsGC+RqcG5UvVM
iMPhnwe/bXEehShK86yJK/g/UiKrO87h3aEu5gcJqBygTq3BBBoH2md3pr/W+hUM
WBsCQQChfhTIrdDinKi6lRxrdBnn0Ohjg2cwuqK5zzU9p/N+S9x7Ck8wUI53DKm8
jUJE8WAG7WLj/oCOWEh+ic6NIwTdAkEAj0X8nhx6AXsgCYRql1klbqtVmL8+95KZ
K7PnLWG/IfjQUy3pPGoSaZ7fdquG8bq8oyf5+dzjE/oTXcByS+6XRQJAP/5ciy1b
L3NhUhsaOVy55MHXnPjdcTX0FaLi+ybXZIfIQ2P4rb19mVq1feMbCXhz+L1rG8oa
t5lYKfpe8k83ZA==
-----END PRIVATE KEY-----`;
            
            const bodykiJson = this.rsaDecrypt(dataResponse.keys, privateKey);
            if (!bodykiJson) {
                console.error("RSA解密失败");
                return null;
            }
            
            const bodyki = JSON.parse(bodykiJson);
            
            // AES解密响应数据
            const decryptedData = this.aesDecrypt(dataResponse.response_key, bodyki.key, bodyki.iv);
            if (!decryptedData) {
                console.error("AES解密失败");
                return null;
            }
            
            const result = JSON.parse(decryptedData);
            
            const endTime = Date.now();
            console.log(`数据获取耗时: ${(endTime - startTime) / 1000}秒, 路径: ${path}`);
            
            // 缓存结果
            if (useCache && cacheKey) {
                this.cache[cacheKey] = [result, Date.now() / 1000];
            }
            
            return result;
            
        } catch (e) {
            console.error(`获取数据失败: ${e}, 路径: ${path}`);
            return null;
        }
    }

    getMd5(text) {
        return crypto.createHash('md5').update(text).digest('hex');
    }

    // 简单的哈希函数，用于生成缓存键
    hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 转换为32位整数
        }
        return Math.abs(hash);
    }
}

module.exports = Spider;
