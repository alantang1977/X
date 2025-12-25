const CryptoJS = require('crypto-js');
const NodeRSA = require('node-rsa');
const md5 = require('md5');

let host = 'https://api.w32z7vtd.com';
let token = '1be86e8e18a9fa18b2b8d5432699dad0.ac008ed650fd087bfbecf2fda9d82e9835253ef24843e6b18fcd128b10763497bcf9d53e959f5377cde038c20ccf9d17f604c9b8bb6e61041def86729b2fc7408bd241e23c213ac57f0226ee656e2bb0a583ae0e4f3bf6c6ab6c490c9a6f0d8cdfd366aacf5d83193671a8f77cd1af1ff2e9145de92ec43ec87cf4bdc563f6e919fe32861b0e93b118ec37d8035fbb3c.59dd05c5d9a8ae726528783128218f15fe6f2c0c8145eddab112b374fcfe3d79';
let headers = {
    'Cache-Control': 'no-cache',
    'Version': '2406025',
    'PackageName': 'com.uf076bf0c246.qe439f0d5e.m8aaf56b725a.ifeb647346f',
    'Ver': '1.9.2',
    'Referer': host,
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'okhttp/3.12.0'
};

// 缓存机制
let cache = {};
const cacheTimeout = 300; // 5分钟缓存

async function init(cfg) {}

/**
 * AES加密
 * @param {string} text 待加密文本
 * @param {string} key 密钥
 * @param {string} iv 偏移量
 * @returns {string} 加密后的数据
 */
function aesEncrypt(text, key, iv) {
    try {
        const keyBytes = CryptoJS.enc.Utf8.parse(key);
        const ivBytes = CryptoJS.enc.Utf8.parse(iv);
        const encrypted = CryptoJS.AES.encrypt(text, keyBytes, {
            iv: ivBytes,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        return encrypted.ciphertext.toString().toUpperCase();
    } catch (e) {
        console.error(`AES加密失败: ${e}`);
        return "";
    }
}

/**
 * AES解密
 * @param {string} text 待解密文本
 * @param {string} key 密钥
 * @param {string} iv 偏移量
 * @returns {string} 解密后的数据
 */
function aesDecrypt(text, key, iv) {
    try {
        const keyBytes = CryptoJS.enc.Utf8.parse(key);
        const ivBytes = CryptoJS.enc.Utf8.parse(iv);
        const encryptedHex = CryptoJS.enc.Hex.parse(text);
        const encryptedBase64 = CryptoJS.enc.Base64.stringify(encryptedHex);
        const decrypted = CryptoJS.AES.decrypt(encryptedBase64, keyBytes, {
            iv: ivBytes,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        return decrypted.toString(CryptoJS.enc.Utf8);
    } catch (e) {
        console.error(`AES解密失败: ${e}`);
        return "";
    }
}

/**
 * RSA解密
 * @param {string} encryptedData 加密数据
 * @param {string} privateKey 私钥
 * @returns {string} 解密后的数据
 */
function rsaDecrypt(encryptedData, privateKey) {
    try {
        const key = new NodeRSA(privateKey);
        key.setOptions({ encryptionScheme: 'pkcs1' });
        const decrypted = key.decrypt(encryptedData, 'utf8');
        return decrypted;
    } catch (e) {
        console.error(`RSA解密失败: ${e}`);
        return "";
    }
}

/**
 * 带缓存的数据获取
 * @param {string} cacheKey 缓存键
 * @param {object} data 请求数据
 * @param {string} path 请求路径
 * @returns {Promise<object>} 响应数据
 */
async function getCachedData(cacheKey, data, path) {
    const currentTime = Date.now() / 1000;
    if (cache[cacheKey]) {
        const [cachedData, timestamp] = cache[cacheKey];
        if (currentTime - timestamp < cacheTimeout) {
            return cachedData;
        }
    }

    // 缓存不存在或已过期，重新获取
    const result = await getData(data, path);
    if (result) {
        cache[cacheKey] = [result, currentTime];
    }
    return result;
}

/**
 * 获取数据的主要方法
 * @param {object} data 请求数据
 * @param {string} path 请求路径
 * @param {boolean} useCache 是否使用缓存
 * @returns {Promise<object>} 响应数据
 */
async function getData(data, path, useCache = true) {
    try {
        // 构建缓存键
        let cacheKey = useCache ? `${path}_${md5(JSON.stringify(data))}` : null;
        
        if (useCache && cacheKey && cache[cacheKey]) {
            const [cachedData, timestamp] = cache[cacheKey];
            if (Date.now() / 1000 - timestamp < cacheTimeout) {
                return cachedData;
            }
        }

        const startTime = Date.now();
        
        // AES加密请求数据
        const requestKey = aesEncrypt(JSON.stringify(data), 'mvXBSW7ekreItNsT', '2U3IrJL8szAKp0Fj');
        if (!requestKey) {
            return null;
        }
        
        // 生成签名
        const t = Math.floor(Date.now() / 1000).toString();
        const keys = "Qmxi5ciWXbQzkr7o+SUNiUuQxQEf8/AVyUWY4T/BGhcXBIUz4nOyHBGf9A4KbM0iKF3yp9M7WAY0rrs5PzdTAOB45plcS2zZ0wUibcXuGJ29VVGRWKGwE9zu2vLwhfgjTaaDpXo4rby+7GxXTktzJmxvneOUdYeHi+PZsThlvPI=";
        const signStr = `token_id=,token=${token},phone_type=1,request_key=${requestKey},app_id=1,time=${t},keys=${keys}*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br`;
        const signature = md5(signStr);
        
        // 构建请求体
        const body = new URLSearchParams({
            'token': token,
            'token_id': '',
            'phone_type': '1',
            'time': t,
            'phone_model': 'xiaomi-22021211rc',
            'keys': keys,
            'request_key': requestKey,
            'signature': signature,
            'app_id': '1',
            'ad_version': '1'
        });
        
        // 发送请求
        const url = `${host}${path}`;
        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: body.toString(),
            timeout: 10000
        });
        
        if (!response.ok) {
            console.error(`API请求失败: ${response.status}, 路径: ${path}`);
            return null;
        }
        
        const responseData = await response.json();
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
        
        const bodykiJson = rsaDecrypt(dataResponse.keys, privateKey);
        if (!bodykiJson) {
            console.error("RSA解密失败");
            return null;
        }
        
        const bodyki = JSON.parse(bodykiJson);
        
        // AES解密响应数据
        const decryptedData = aesDecrypt(dataResponse.response_key, bodyki.key, bodyki.iv);
        if (!decryptedData) {
            console.error("AES解密失败");
            return null;
        }
        
        const result = JSON.parse(decryptedData);
        
        const endTime = Date.now();
        console.log(`数据获取耗时: ${(endTime - startTime) / 1000}秒, 路径: ${path}`);
        
        // 缓存结果
        if (useCache && cacheKey) {
            cache[cacheKey] = [result, Date.now() / 1000];
        }
        
        return result;
    } catch (e) {
        console.error(`获取数据失败: ${e}, 路径: ${path}`);
        return null;
    }
}

/**
 * 首页内容
 * @param {object} filter 筛选条件
 * @returns {Promise<string>} JSON字符串
 */
async function home(filter) {
    const classes = [
        {"type_name": "电影", "type_id": "1"},
        {"type_name": "电视剧", "type_id": "2"},
        {"type_name": "动漫", "type_id": "4"},
        {"type_name": "综艺", "type_id": "3"},
        {"type_name": "短剧", "type_id": "64"}
    ];
    
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
    
    return JSON.stringify({
        class: classes,
        filters: filters
    });
}

/**
 * 首页视频内容
 * @returns {Promise<string>} JSON字符串
 */
async function homeVod() {
    // 首页推荐直接返回空列表
    return JSON.stringify({ list: [] });
}

/**
 * 分类内容
 * @param {string} tid 分类ID
 * @param {string} pg 页码
 * @param {object} filter 筛选条件
 * @param {object} extend 扩展参数
 * @returns {Promise<string>} JSON字符串
 */
async function category(tid, pg, filter, extend) {
    try {
        const body = {
            "area": extend?.area || '0',
            "year": extend?.year || '0',
            "pageSize": "30",
            "sort": extend?.sort || 'd_id',
            "page": pg.toString(),
            "tid": tid
        };
        
        const cacheKey = `category_${tid}_${pg}_${md5(JSON.stringify(body))}`;
        const data = await getCachedData(cacheKey, body, '/App/IndexList/indexList');
        
        const videos = [];
        if (data && data.list) {
            for (const item of data.list) {
                const vodContinu = item.vod_continu || 0;
                const remarks = vodContinu === 0 ? '电影' : `更新至${vodContinu}集`;
                
                videos.push({
                    "vod_id": `${item.vod_id || ''}/${vodContinu}`,
                    "vod_name": item.vod_name || '',
                    "vod_pic": item.vod_pic || '',
                    "vod_remarks": remarks
                });
            }
        }
        
        return JSON.stringify({
            'list': videos,
            'page': parseInt(pg),
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        });
    } catch (e) {
        console.error(`获取分类内容失败: ${e}`);
        return JSON.stringify({ list: [] });
    }
}

/**
 * 视频详情
 * @param {string} id 视频ID
 * @returns {Promise<string>} JSON字符串
 */
async function detail(id) {
    try {
        const vodId = id.split('/')[0];
        
        // 获取视频详情
        const t = Math.floor(Date.now() / 1000).toString();
        const body1 = {
            "token_id": "1649412",
            "vod_id": vodId,
            "mobile_time": t,
            "token": token
        };
        const qdata = await getData(body1, '/App/IndexPlay/playInfo');
        
        // 获取播放列表
        const body2 = {
            "vurl_cloud_id": "2",
            "vod_d_id": vodId
        };
        const jdata = await getData(body2, '/App/Resource/Vurl/show');
        
        if (!qdata || !qdata.vodInfo) {
            return JSON.stringify({ list: [] });
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
                        const value = item.play[key];
                        if (value.param) {
                            n.push(key);
                            p.push(value.param);
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
        
        return JSON.stringify({ list: [videoDetail] });
    } catch (e) {
        console.error(`获取详情失败: ${e}`);
        return JSON.stringify({ list: [] });
    }
}

/**
 * 搜索功能
 * @param {string} wd 搜索关键词
 * @param {boolean} quick 快速搜索
 * @param {string} pg 页码
 * @returns {Promise<string>} JSON字符串
 */
async function search(wd, quick, pg = 1) {
    try {
        const body = {
            "keywords": wd,
            "order_val": "1",
            "page": pg.toString()
        };
        
        // 搜索不使用缓存，确保实时性
        const startTime = Date.now();
        const data = await getData(body, '/App/Index/findMoreVod', false);
        const endTime = Date.now();
        
        console.log(`搜索请求耗时: ${(endTime - startTime) / 1000}秒`);
        
        const videos = [];
        if (data && data.list) {
            for (const item of data.list) {
                const vodContinu = item.vod_continu || 0;
                const remarks = vodContinu === 0 ? '电影' : `更新至${vodContinu}集`;
                
                videos.push({
                    "vod_id": `${item.vod_id || ''}/${vodContinu}`,
                    "vod_name": item.vod_name || '',
                    "vod_pic": item.vod_pic || '',
                    "vod_remarks": remarks
                });
            }
        }
        
        return JSON.stringify({
            'list': videos,
            'page': parseInt(pg),
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        });
    } catch (e) {
        console.error(`搜索失败: ${e}`);
        return JSON.stringify({ list: [] });
    }
}

/**
 * 播放解析
 * @param {string} flag 标志
 * @param {string} id 播放ID
 * @param {string} flags 标志列表
 * @returns {Promise<string>} JSON字符串
 */
async function play(flag, id, flags) {
    try {
        // 解析播放信息
        const parts = id.split('||');
        if (parts.length < 2) {
            return JSON.stringify({ parse: 0, playUrl: "", url: "" });
        }
        
        const paramStr = parts[0];
        const resolutions = parts.length > 1 ? parts[1].split('@') : [];
        
        // 解析参数
        const params = {};
        paramStr.split('&').forEach(pair => {
            const [key, value] = pair.split('=', 1);
            if (key && value) {
                params[key] = value;
            }
        });
        
        // 获取播放链接
        if (resolutions.length > 0) {
            // 分辨率从大到小排序
            resolutions.sort((a, b) => {
                const numA = parseInt(a) || 0;
                const numB = parseInt(b) || 0;
                return numB - numA;
            });
            
            // 使用最大分辨率
            params.resolution = resolutions[0];
            const body = params;
            
            const startTime = Date.now();
            const data = await getData(body, '/App/Resource/VurlDetail/showOne', false);
            const endTime = Date.now();
            console.log(`播放链接获取耗时: ${(endTime - startTime) / 1000}秒`);
            
            if (data && data.url) {
                return JSON.stringify({
                    "parse": 0,
                    "playUrl": "",
                    "url": data.url,
                    "header": JSON.stringify(headers)
                });
            }
        }
        
        return JSON.stringify({ parse: 0, playUrl: "", url: "" });
    } catch (e) {
        console.error(`播放解析失败: ${e}`);
        return JSON.stringify({ parse: 0, playUrl: "", url: "" });
    }
}

export default { init, home, homeVod, category, detail, search, play };