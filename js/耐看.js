const crypto = require("crypto");
const axios = require("axios");
const cheerio = require("cheerio");
const https = require("https");

// ========== 全局配置 ==========
const HOST = 'https://nkvod.org';
const UA = 'Mozilla/5.0 (Linux; Android 12; ALN-AL00 Build/HUAWEIALN-AL00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/114.0.5735.196 Mobile Safari/537.36';

// ========== 缓存系统 ==========
class CacheManager {
    constructor(ttl = 300000) {
        this.cache = new Map();
        this.ttl = ttl;
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;
        
        if (Date.now() - item.timestamp > this.ttl) {
            this.cache.delete(key);
            return null;
        }
        
        return item.data;
    }

    set(key, data) {
        this.cache.set(key, { data, timestamp: Date.now() });
    }

    clear() {
        this.cache.clear();
    }
}

const cache = new CacheManager();
let searchCookie = '';

// ========== HTTP 请求工具 ==========
const requestUtil = {
    // 创建 axios 实例
    createInstance: () => {
        return axios.create({
            httpsAgent: new https.Agent({ 
                rejectUnauthorized: false,
                keepAlive: true,
                maxSockets: 5
            }),
            timeout: 15000,
            maxRedirects: 0,
            headers: {
                'User-Agent': UA,
                'Referer': HOST
            }
        });
    },

    // 通用请求函数
    request: async (url, options = {}) => {
        const instance = requestUtil.createInstance();
        const defaultOptions = {
            method: 'GET',
            headers: {
                'User-Agent': UA,
                'Referer': HOST
            }
        };

        if (searchCookie) {
            defaultOptions.headers.Cookie = searchCookie;
        }

        const mergedOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await instance({
                url,
                ...mergedOptions
            });
            return response.data;
        } catch (error) {
            throw error;
        }
    },

    // 请求二进制数据
    requestBinary: async (url, options = {}) => {
        const instance = requestUtil.createInstance();
        const defaultOptions = {
            method: 'GET',
            headers: {
                'User-Agent': UA,
                'Referer': HOST
            },
            responseType: 'arraybuffer'
        };

        if (searchCookie) {
            defaultOptions.headers.Cookie = searchCookie;
        }

        try {
            const response = await instance({
                url,
                ...defaultOptions,
                ...options
            });
            
            return {
                headers: response.headers,
                binaryData: Buffer.from(response.data)
            };
        } catch (error) {
            throw error;
        }
    },

    // 带验证码处理的请求
    requestWithCaptcha: async (url, verifyType = 'search', options = {}) => {
        try {
            let html = await requestUtil.request(url, options);
            
            const needCaptcha = html && (
                html.includes('系统安全验证') || 
                html.includes('请输入验证码') ||
                html.includes('verify/index.html') ||
                html.includes('verify_check')
            );
            
            if (needCaptcha) {
                searchCookie = '';
                await fetchCk(verifyType);
                
                if (searchCookie) {
                    html = await requestUtil.request(url, {
                        ...options,
                        headers: {
                            ...options.headers,
                            'Cookie': searchCookie
                        }
                    });
                }
                
                const stillNeedCaptcha = html && (
                    html.includes('系统安全验证') || 
                    html.includes('请输入验证码')
                );
                
                if (stillNeedCaptcha) {
                    return null;
                }
            }
            
            return html;
        } catch (error) {
            throw error;
        }
    }
};

// ========== 验证码处理 ==========
async function fetchCk(verifyType = 'search') {
    try {
        const yzm = `${HOST}/index.php/verify/index.html?${Date.now()}`;
        const yzmResponse = await requestUtil.requestBinary(yzm);
        
        let cookie = "";
        const headers = yzmResponse.headers;
        
        if (headers['set-cookie']) {
            const cookieValue = headers['set-cookie'];
            if (Array.isArray(cookieValue)) {
                cookie = cookieValue[0].split(";")[0];
            } else if (typeof cookieValue === 'string') {
                cookie = cookieValue.split(";")[0];
            }
        }
        
        if (!cookie) {
            return;
        }

        const base64Image = yzmResponse.binaryData.toString('base64');
        
        if (!base64Image) {
            return;
        }
        
        try {
            // 使用OCR API识别验证码
            const ocrResponse = await axios.post("https://api.nn.ci/ocr/b64/text", base64Image, {
                headers: { 
                    'Content-Type': 'text/plain',
                    'User-Agent': UA,
                    'Accept': 'application/json'
                },
                timeout: 10000
            });
            
            if (!ocrResponse || !ocrResponse.data) {
                return;
            }
            
            let verifyCode = ocrResponse.data.trim();
            if (!verifyCode) {
                return;
            }
            
            verifyCode = verifyCode.replace(/[^a-zA-Z0-9]/g, '');
            
            if (verifyCode.length < 4) {
                return;
            }
            
            const submit_url = `${HOST}/index.php/ajax/verify_check?type=${verifyType}&verify=${verifyCode}`;
            
            const submitResponse = await axios.post(submit_url, '', {
                headers: {
                    'User-Agent': UA,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': HOST,
                    'Referer': HOST + '/',
                    'Cookie': cookie,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });
            
            if (submitResponse && submitResponse.data) {
                const submitData = submitResponse.data;
                if (typeof submitData === 'object' && submitData.code === 1) {
                    searchCookie = cookie;
                } else if (typeof submitData === 'string' && 
                          (submitData.includes('"code":1') || submitData.includes('验证成功'))) {
                    searchCookie = cookie;
                }
            }
            
        } catch (ocrError) {
            // 忽略OCR错误
        }
    } catch (error) {
        // 忽略错误
    }
}

// ========== 辅助函数 ==========
function getText($elem) {
    if (!$elem || $elem.length === 0) return '';
    
    let text = $elem.text().trim();
    if (!text) {
        const html = $elem.html();
        if (html) {
            text = html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        }
    }
    
    return text;
}

function getFilterValue(filterGroup, key, extend) {
    const filterItem = filterGroup.find(item => item.key === key);
    if (!filterItem) return '';
    
    const userValue = extend[key];
    if (userValue) {
        const option = filterItem.value.find(opt => opt.v === userValue);
        return option ? option.v : '';
    }
    
    return filterItem.value[0].v;
}

// ========== 解密函数 ==========
function decryptData(encryptedHex, rawKeyArray, ivArray) {
    if (!validateHexData(encryptedHex)) {
        return null;
    }
    
    const rawKey = Buffer.from(rawKeyArray);
    const iv = Buffer.from(ivArray);
    const encrypted = Buffer.from(encryptedHex, 'hex');

    // 尝试不同的 AES 模式
    const modes = [
        { name: 'CBC', mode: 'aes-128-cbc' },
        { name: 'OFB', mode: 'aes-128-ofb' },
        { name: 'CTR', mode: 'aes-128-ctr' },
        { name: 'ECB', mode: 'aes-128-ecb' },
        { name: 'CFB', mode: 'aes-128-cfb' }
    ];

    for (let modeInfo of modes) {
        try {
            let decipher;
            if (modeInfo.name === 'ECB') {
                decipher = crypto.createDecipheriv(modeInfo.mode, rawKey, null);
            } else {
                decipher = crypto.createDecipheriv(modeInfo.mode, rawKey, iv);
            }
            
            decipher.setAutoPadding(true);
            
            let decrypted = decipher.update(encrypted);
            decrypted = Buffer.concat([decrypted, decipher.final()]);
            
            const result = decrypted.toString('utf8');
            if (result && result.length > 0) {
                return result;
            }
        } catch (e) {
            // 继续尝试其他模式
        }
    }
    
    return null;
}

function validateHexData(hexStr) {
    if (hexStr.length % 2 !== 0) {
        return false;
    }
    if (!/^[0-9a-fA-F]+$/.test(hexStr)) {
        return false;
    }
    return true;
}

function getrandom(b) {
    try {
        const string = b.substring(10);
        let substr;
        
        try {
            const base64Data = Buffer.from(string, 'base64');
            substr = base64Data.toString('latin1');
        } catch (e) {
            throw new Error('Base64解码失败');
        }

        if (!substr) {
            throw new Error('Base64解码结果为空');
        }

        const substrTrim = substr.substring(10);
        let data2 = substrTrim.replace('_nanke', '');
        let data3 = data2.slice(0, 20) + data2.slice(21);
        const hexStr = data3.replace(/[^0-9a-fA-F]/g, '');
        const finalUrl = hexDecodeAndFilter(hexStr);
        return finalUrl;
    } catch (error) {
        throw error;
    }
}

function hexDecodeAndFilter(hexStr) {
    try {
        let pureHex = hexStr.replace(/[^0-9a-fA-F]/g, '');
        if (pureHex.length % 2 !== 0) {
            pureHex += '0';
        }
        
        let decoded = '';
        for (let i = 0; i < pureHex.length; i += 2) {
            const hexByte = pureHex.substr(i, 2);
            const charCode = parseInt(hexByte, 16);
            const char = String.fromCharCode(charCode);
            const isUrlValid = /[a-zA-Z0-9:\/\.\-\?\&=\%]/.test(char);
            if (isUrlValid) {
                decoded += char;
            }
        }
        
        const urlMatch = decoded.match(/https?:\/\/[^\s]+/);
        decoded = urlMatch ? urlMatch[0] : decoded.trim();
        return decoded;
    } catch (e) {
        throw e;
    }
}

// ========== 主要功能函数 ==========
const _home = async ({ filter }) => {
    const classes = [
        { type_id: "1", type_name: "电影" },
        { type_id: "2", type_name: "剧集" },
        { type_id: "4", type_name: "动漫" },
        { type_id: "3", type_name: "综艺" }                      
    ];

    const filterObj = {
        "1": [
            {"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"喜剧","v":"喜剧"},{"n":"爱情","v":"爱情"},{"n":"恐怖","v":"恐怖"},{"n":"动作","v":"动作"},{"n":"科幻","v":"科幻"},{"n":"剧情","v":"剧情"},{"n":"战争","v":"战争"},{"n":"警匪","v":"警匪"},{"n":"犯罪","v":"犯罪"},{"n":"动画","v":"动画"},{"n":"奇幻","v":"奇幻"},{"n":"武侠","v":"武侠"},{"n":"冒险","v":"冒险"},{"n":"枪战","v":"枪战"},{"n":"悬疑","v":"悬疑"},{"n":"惊悚","v":"惊悚"},{"n":"经典","v":"经典"},{"n":"青春","v":"青春"},{"n":"文艺","v":"文艺"},{"n":"微电影","v":"微电影"},{"n":"古装","v":"古装"},{"n":"历史","v":"历史"},{"n":"运动","v":"运动"},{"n":"农村","v":"农村"},{"n":"儿童","v":"儿童"},{"n":"网络电影","v":"网络电影"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"大陆","v":"大陆"},{"n":"香港","v":"香港"},{"n":"台湾","v":"台湾"},{"n":"美国","v":"美国"},{"n":"法国","v":"法国"},{"n":"英国","v":"英国"},{"n":"日本","v":"日本"},{"n":"韩国","v":"韩国"},{"n":"德国","v":"德国"},{"n":"泰国","v":"泰国"},{"n":"印度","v":"印度"},{"n":"意大利","v":"意大利"},{"n":"西班牙","v":"西班牙"},{"n":"加拿大","v":"加拿大"},{"n":"其它","v":"其它"}]},
            {"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"}]},
            {"key":"lang","name":"语言","value":[{"n":"全部","v":""},{"n":"国语","v":"国语"},{"n":"英语","v":"英语"},{"n":"粤语","v":"粤语"},{"n":"闽南语","v":"闽南语"},{"n":"韩语","v":"韩语"},{"n":"日语","v":"日语"},{"n":"法语","v":"法语"},{"n":"德语","v":"德语"},{"n":"其它","v":"其它"}]},
            {"key":"letter","name":"字母","value":[{"n":"字母","v":""},{"n":"A","v":"A"},{"n":"B","v":"B"},{"n":"C","v":"C"},{"n":"D","v":"D"},{"n":"E","v":"E"},{"n":"F","v":"F"},{"n":"G","v":"G"},{"n":"H","v":"H"},{"n":"I","v":"I"},{"n":"J","v":"J"},{"n":"K","v":"K"},{"n":"L","v":"L"},{"n":"M","v":"M"},{"n":"N","v":"N"},{"n":"O","v":"O"},{"n":"P","v":"P"},{"n":"Q","v":"Q"},{"n":"R","v":"R"},{"n":"S","v":"S"},{"n":"T","v":"T"},{"n":"U","v":"U"},{"n":"V","v":"V"},{"n":"W","v":"W"},{"n":"X","v":"X"},{"n":"Y","v":"Y"},{"n":"Z","v":"Z"},{"n":"0-9","v":"0-9"}]},
            {"key":"by","name":"排序","value":[{"n":"时间排序","v":"time"},{"n":"人气排序","v":"hits"},{"n":"评分排序","v":"score"}]}
        ],
        "2": [
            {"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"古装","v":"古装"},{"n":"战争","v":"战争"},{"n":"青春偶像","v":"青春偶像"},{"n":"喜剧","v":"喜剧"},{"n":"动作","v":"动作"},{"n":"奇幻","v":"奇幻"},{"n":"剧情","v":"剧情"},{"n":"历史","v":"历史"},{"n":"经典","v":"经典"},{"n":"乡村","v":"乡村"},{"n":"情景","v":"情景"},{"n":"商战","v":"商战"},{"n":"网剧","v":"网剧"},{"n":"其他","v":"其他"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"内地","v":"内地"},{"n":"韩国","v":"韩国"},{"n":"香港","v":"香港"},{"n":"台湾","v":"台湾"},{"n":"日本","v":"日本"},{"n":"美国","v":"美国"},{"n":"泰国","v":"泰国"},{"n":"英国","v":"英国"},{"n":"新加坡","v":"新加坡"},{"n":"其他","v":"其他"}]},
            {"key":"lang","name":"语言","value":[{"n":"全部","v":""},{"n":"国语","v":"国语"},{"n":"英语","v":"英语"},{"n":"粤语","v":"粤语"},{"n":"闽南语","v":"闽南语"},{"n":"韩语","v":"韩语"},{"n":"日语","v":"日语"},{"n":"其它","v":"其它"}]},
            {"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"},{"n":"2009","v":"2009"},{"n":"2008","v":"2008"},{"n":"2006","v":"2006"},{"n":"2005","v":"2005"},{"n":"2004","v":"2004"}]},
            {"key":"letter","name":"字母","value":[{"n":"字母","v":""},{"n":"A","v":"A"},{"n":"B","v":"B"},{"n":"C","v":"C"},{"n":"D","v":"D"},{"n":"E","v":"E"},{"n":"F","v":"F"},{"n":"G","v":"G"},{"n":"H","v":"H"},{"n":"I","v":"I"},{"n":"J","v":"J"},{"n":"K","v":"K"},{"n":"L","v":"L"},{"n":"M","v":"M"},{"n":"N","v":"N"},{"n":"O","v":"O"},{"n":"P","v":"P"},{"n":"Q","v":"Q"},{"n":"R","v":"R"},{"n":"S","v":"S"},{"n":"T","v":"T"},{"n":"U","v":"U"},{"n":"V","v":"V"},{"n":"W","v":"W"},{"n":"X","v":"X"},{"n":"Y","v":"Y"},{"n":"Z","v":"Z"},{"n":"0-9","v":"0-9"}]},
            {"key":"by","name":"排序","value":[{"n":"时间排序","v":"time"},{"n":"人气排序","v":"hits"},{"n":"评分排序","v":"score"}]}
        ],
        "3": [
            {"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"选秀","v":"选秀"},{"n":"情感","v":"情感"},{"n":"访谈","v":"访谈"},{"n":"播报","v":"播报"},{"n":"旅游","v":"旅游"},{"n":"音乐","v":"音乐"},{"n":"美食","v":"美食"},{"n":"纪实","v":"纪实"},{"n":"曲艺","v":"曲艺"},{"n":"生活","v":"生活"},{"n":"游戏互动","v":"游戏互动"},{"n":"财经","v":"财经"},{"n":"求职","v":"求职"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"内地","v":"内地"},{"n":"港台","v":"港台"},{"n":"日韩","v":"日韩"},{"n":"欧美","v":"欧美"}]},
            {"key":"lang","name":"语言","value":[{"n":"全部","v":""},{"n":"国语","v":"国语"},{"n":"英语","v":"英语"},{"n":"粤语","v":"粤语"},{"n":"闽南语","v":"闽南语"},{"n":"韩语","v":"韩语"},{"n":"日语","v":"日语"},{"n":"其它","v":"其它"}]},
            {"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"},{"n":"2009","v":"2009"},{"n":"2008","v":"2008"},{"n":"2007","v":"2007"},{"n":"2006","v":"2006"},{"n":"2005","v":"2005"},{"n":"2004","v":"2004"}]},
            {"key":"letter","name":"字母","value":[{"n":"字母","v":""},{"n":"A","v":"A"},{"n":"B","v":"B"},{"n":"C","v":"C"},{"n":"D","v":"D"},{"n":"E","v":"E"},{"n":"F","v":"F"},{"n":"G","v":"G"},{"n":"H","v":"H"},{"n":"I","v":"I"},{"n":"J","v":"J"},{"n":"K","v":"K"},{"n":"L","v":"L"},{"n":"M","v":"M"},{"n":"N","v":"N"},{"n":"O","v":"O"},{"n":"P","v":"P"},{"n":"Q","v":"Q"},{"n":"R","v":"R"},{"n":"S","v":"S"},{"n":"T","v":"T"},{"n":"U","v":"U"},{"n":"V","v":"V"},{"n":"W","v":"W"},{"n":"X","v":"X"},{"n":"Y","v":"Y"},{"n":"Z","v":"Z"},{"n":"0-9","v":"0-9"}]},
            {"key":"by","name":"排序","value":[{"n":"时间排序","v":"time"},{"n":"人气排序","v":"hits"},{"n":"评分排序","v":"score"}]}
        ],
        "4": [
            {"key":"class","name":"剧情","value":[{"n":"全部","v":""},{"n":"情感","v":"情感"},{"n":"科幻","v":"科幻"},{"n":"热血","v":"热血"},{"n":"推理","v":"推理"},{"n":"搞笑","v":"搞笑"},{"n":"冒险","v":"冒险"},{"n":"萝莉","v":"萝莉"},{"n":"校园","v":"校园"},{"n":"动作","v":"动作"},{"n":"机战","v":"机战"},{"n":"运动","v":"运动"},{"n":"战争","v":"战争"},{"n":"少年","v":"少年"},{"n":"少女","v":"少女"},{"n":"社会","v":"社会"},{"n":"原创","v":"原创"},{"n":"亲子","v":"亲子"},{"n":"益智","v":"益智"},{"n":"励志","v":"励志"},{"n":"其他","v":"其他"}]},
            {"key":"area","name":"地区","value":[{"n":"全部","v":""},{"n":"国产","v":"国产"},{"n":"日本","v":"日本"},{"n":"欧美","v":"欧美"},{"n":"其他","v":"其他"}]},
            {"key":"lang","name":"语言","value":[{"n":"全部","v":""},{"n":"国语","v":"国语"},{"n":"英语","v":"英语"},{"n":"粤语","v":"粤语"},{"n":"闽南语","v":"闽南语"},{"n":"韩语","v":"韩语"},{"n":"日语","v":"日语"},{"n":"其它","v":"其它"}]},
            {"key":"year","name":"年份","value":[{"n":"全部","v":""},{"n":"2026","v":"2026"},{"n":"2025","v":"2025"},{"n":"2024","v":"2024"},{"n":"2023","v":"2023"},{"n":"2022","v":"2022"},{"n":"2021","v":"2021"},{"n":"2020","v":"2020"},{"n":"2019","v":"2019"},{"n":"2018","v":"2018"},{"n":"2017","v":"2017"},{"n":"2016","v":"2016"},{"n":"2015","v":"2015"},{"n":"2014","v":"2014"},{"n":"2013","v":"2013"},{"n":"2012","v":"2012"},{"n":"2011","v":"2011"},{"n":"2010","v":"2010"},{"n":"2009","v":"2009"},{"n":"2008","v":"2008"},{"n":"2007","v":"2007"},{"n":"2006","v":"2006"},{"n":"2005","v":"2005"},{"n":"2004","v":"2004"}]},
            {"key":"letter","name":"字母","value":[{"n":"字母","v":""},{"n":"A","v":"A"},{"n":"B","v":"B"},{"n":"C","v":"C"},{"n":"D","v":"D"},{"n":"E","v":"E"},{"n":"F","v":"F"},{"n":"G","v":"G"},{"n":"H","v":"H"},{"n":"I","v":"I"},{"n":"J","v":"J"},{"n":"K","v":"K"},{"n":"L","v":"L"},{"n":"M","v":"M"},{"n":"N","v":"N"},{"n":"O","v":"O"},{"n":"P","v":"P"},{"n":"Q","v":"Q"},{"n":"R","v":"R"},{"n":"S","v":"S"},{"n":"T","v":"T"},{"n":"U","v":"U"},{"n":"V","v":"V"},{"n":"W","v":"W"},{"n":"X","v":"X"},{"n":"Y","v":"Y"},{"n":"Z","v":"Z"},{"n":"0-9","v":"0-9"}]},
            {"key":"by","name":"排序","value":[{"n":"时间排序","v":"time"},{"n":"人气排序","v":"hits"},{"n":"评分排序","v":"score"}]}
        ]
    };

    return {
        class: classes,
        filters: filterObj
    };
};

const _homeVod = async ({ filter }) => {
    const link = `${HOST}/`;
    try {
        const html = await requestUtil.request(link);
        if (!html) return { list: [] };
        
        const $ = cheerio.load(html);
        const hotSection = $('.title-a:contains("热播推荐")').closest('.box-width');
        if (hotSection.length === 0) return { list: [] };
        
        const items = hotSection.find('.public-list-box');
        if (items.length === 0) return { list: [] };
        
        const videos = items.map((index, item) => {
            const $item = $(item);
            const $link = $item.find('.public-list-exp');
            const $img = $item.find('.gen-movie-img');
            const $title = $item.find('.time-title');
            const $subtitle = $item.find('.public-list-subtitle');
            
            const href = $link.attr('href');
            const title = $title.attr('title') || getText($title);
            const imgSrc = $img.attr('data-src');
            const remarks = getText($subtitle);
            
            const vod_id = href && href.startsWith('http') ? href : HOST + (href || '');
            const vod_name = title;
            const vod_pic = imgSrc ? (imgSrc.startsWith('http') ? imgSrc : HOST + imgSrc) : '';
            const vod_remarks = remarks;
            
            return {
                vod_id,
                vod_name,
                vod_pic,
                vod_remarks
            };
        }).get();
        
        return { list: videos };
    } catch (error) {
        return { list: [] };
    }
};

const _category = async ({ id, page, filters }) => {
    const tid = id;
    const pg = page || 1;
    
    try {
        const homeData = await _home({});
        const filterObj = homeData.filters;
        if (!filterObj) return { list: [] };
        
        const filterGroup = filterObj[tid];
        if (!filterGroup) return { list: [] };
        
        const area = getFilterValue(filterGroup, 'area', filters || {});
        const by = getFilterValue(filterGroup, 'by', filters || {});
        const classValue = getFilterValue(filterGroup, 'class', filters || {});
        const lang = getFilterValue(filterGroup, 'lang', filters || {});
        const letter = getFilterValue(filterGroup, 'letter', filters || {});
        const year = getFilterValue(filterGroup, 'year', filters || {});
        
        const link = `${HOST}/show/${tid}-${area}-${by}-${classValue}-${lang}-${letter}---${pg}---${year}.html`;
        
        const html = await requestUtil.requestWithCaptcha(link, 'show');
        if (!html) return { list: [] };
        
        const $ = cheerio.load(html);
        
        if ($('.public-list-box').length === 0) {
            return { list: [] };
        }
        
        const videos = $('.public-list-box').map((index, item) => {
            const $item = $(item);
            const $link = $item.find('.public-list-exp');
            const $title = $item.find('.time-title');
            const $img = $item.find('.gen-movie-img');
            const $remarks = $item.find('.public-list-subtitle');
            
            const href = $link.attr('href');
            const title = $title.attr('title') || getText($title);
            const imgSrc = $img.attr('data-src');
            const remarks = getText($remarks);
            
            const vod_id = href && href.startsWith('http') ? href : HOST + (href || '');
            const vod_name = title;
            const vod_pic = imgSrc ? (imgSrc.startsWith('http') ? imgSrc : HOST + imgSrc) : '';
            const vod_remarks = remarks;
            
            return {
                vod_id,
                vod_name,
                vod_pic,
                vod_remarks
            };
        }).get();
        
        return { list: videos };
    } catch (error) {
        return { list: [] };
    }
};

const _search = async ({ wd, page }) => {
    const searchUrl = `${HOST}/nk/-------------.html?wd=${encodeURIComponent(wd)}`;
    const lowerWd = wd.toLowerCase();
    
    try {
        const html = await requestUtil.requestWithCaptcha(searchUrl, 'search');
        if (!html) return { list: [], error: '需要验证码但无法自动识别' };
        
        const $ = cheerio.load(html);
        
        const hasSearchResults = $('.public-list-box.search-box').length > 0;
        const hasSearchInput = $('input[name="wd"]').length > 0;
        const hasSearchHeader = $('.m-search').length > 0;
        
        if ((hasSearchInput || hasSearchHeader) && !hasSearchResults) {
            return { list: [], error: '搜索无结果或需要验证码' };
        }
        
        if (!hasSearchInput && !hasSearchHeader && !hasSearchResults) {
            return { list: [], error: '需要验证码但无法自动识别' };
        }
        
        const videos = [];
        
        $('.public-list-box.search-box').each((index, item) => {
            const $item = $(item);
            const $link = $item.find('.public-list-exp');
            const href = $link.attr('href');
            if (!href) return;
            
            const $title = $item.find('.thumb-txt a');
            const vod_name = getText($title);
            if (!vod_name) return;
            
            const $img = $item.find('.gen-movie-img');
            const vod_pic = $img.attr('data-src');
            
            const $remarks = $item.find('.public-list-prb');
            const vod_remarks = getText($remarks);
            
            const $info = $item.find('.thumb-else');
            const yearText = getText($info.find('a[href*="202"]').first());
            const areaText = getText($info.find('a[href*="美国"], a[href*="英国"], a[href*="泰国"]').first());
            
            const lowerTitle = vod_name.toLowerCase();
            if (lowerTitle.includes(lowerWd)) {
                videos.push({
                    vod_id: HOST + href,
                    vod_name,
                    vod_pic,
                    vod_remarks,
                    vod_year: yearText,
                    vod_area: areaText
                });
            }
        });
        
        return { list: videos };
    } catch (error) {
        return { list: [] };
    }
};

const _detail = async ({ ids }) => {
    if (!ids) return { list: [] };
    
    const id = Array.isArray(ids) ? ids[0] : ids;
    
    try {
        const html = await requestUtil.request(id);
        if (!html) return { list: [] };
        
        const $ = cheerio.load(html);
        
        const vod = {
            vod_id: id,
            vod_name: getText($('.slide-info-title')),
            vod_pic: $('.detail-pic img').attr('data-src') || $('.detail-pic img').attr('src'),
            vod_year: '',
            vod_area: '',
            vod_remarks: '',
            vod_actor: '',
            vod_director: '',
            vod_content: getText($('#height_limit')),
            vod_play_from: '',
            vod_play_url: ''
        };

        $('.slide-info').each((i, elem) => {
            const $elem = $(elem);
            const text = getText($elem);
            
            if (text.includes('备注 :') || text.includes('备注 :')) {
                vod.vod_remarks = text.replace(/备注\s*[:：]/g, '').trim();
            } else if (text.includes('导演 :') || text.includes('导演 :')) {
                vod.vod_director = text.replace(/导演\s*[:：]/g, '').replace(/[\/\s]+$/, '').trim();
            } else if (text.includes('演员 :') || text.includes('演员 :')) {
                vod.vod_actor = text.replace(/演员\s*[:：]/g, '').replace(/[\/\s]+$/, '').trim();
            } else if (text.includes('更新 :') || text.includes('更新 :')) {
                const updateText = text.replace(/更新\s*[:：]/g, '').trim();
                const yearMatch = updateText.match(/\d{4}/);
                if (yearMatch) {
                    vod.vod_year = yearMatch[0];
                }
            }
        });

        // 从链接中提取年份和地区
        const yearLink = $('.slide-info a[href*="202"]').first();
        if (yearLink.length) {
            const yearText = getText(yearLink);
            if (/^\d{4}$/.test(yearText)) vod.vod_year = yearText;
        }
        
        // 尝试从 slide-info-remarks 获取年份和地区
        $('.slide-info-remarks a').each((i, elem) => {
            const $a = $(elem);
            const href = $a.attr('href') || '';
            const aText = getText($a);
            if (/\d{4}/.test(aText) && !vod.vod_year) {
                vod.vod_year = aText.match(/\d{4}/)[0];
            }
            if ((href.includes('内地') || href.includes('香港') || href.includes('台湾') || 
                 href.includes('美国') || href.includes('韩国') || href.includes('日本') ||
                 href.includes('泰国') || href.includes('英国')) && !vod.vod_area) {
                vod.vod_area = aText;
            }
        });

        const playFrom = [];
        const playUrl = [];        
        $('.anthology-tab .swiper-slide').each((i, tab) => {
            const $tab = $(tab);
            let from = $tab.attr('data-from') || '';
            if (!from) from = `nk${i + 1}`; 
            
            let show = getText($tab);
            show = show.replace(/[\ue000-\uf8ff]/g, '')
                       .replace(/&\w+;/g, '')
                       .replace(/\s*\d+\s*$/, '')
                       .trim();
            if (!show) show = from;
            playFrom.push(show);
        });
        
        $('.anthology-list-box').each((i, box) => {
            const episodes = [];
            const $tab = $('.anthology-tab .swiper-slide').eq(i);
            let from = $tab.attr('data-from') || '';
            if (!from) from = `nk${i + 1}`; 
            
            $(box).find('.anthology-list-play a').each((j, link) => {
                const $link = $(link);
                let episodeName = getText($link);
                if (!episodeName) {
                    const href = $link.attr('href') || '';
                    const match = href.match(/-(\d+)\.html$/);
                    episodeName = match ? `第${match[1]}集` : `第${j + 1}集`;
                }
                const episodeUrl = HOST + $link.attr('href');
                episodes.push(`${episodeName}$${episodeUrl}@${from}`);
            });
            playUrl.push(episodes.join('#'));
        });
        
        vod.vod_play_from = playFrom.join('$$$');
        vod.vod_play_url = playUrl.join('$$$');

        return { list: [vod] };
    } catch (error) {
        return { list: [] };
    }
};

const _play = async ({ id, flags }) => {
    try {
        const parts = id.split('@');
        if (parts.length < 2) {
            throw new Error('播放链接格式错误，缺少英文标识');
        }
        
        const playUrl = parts[0]; 
        const from = parts[1];
        const html = await requestUtil.request(playUrl);
        
        const playerStart = html.indexOf('var player_aaaa=');
        if (playerStart === -1) throw new Error('未找到player_aaaa');
        const playerEnd = html.indexOf('</script>', playerStart);
        if (playerEnd === -1) throw new Error('未找到脚本结束标签');

        let playerScript = html.substring(playerStart + 'var player_aaaa='.length, playerEnd);
        playerScript = playerScript.split(';')[0].trim()
            .replace(/,\s*$/, '')
            .replace(/\/\*[\s\S]*?\*\//g, '')
            .replace(/\/\/.*/g, '');

        let playerData;
        try {
            playerData = JSON.parse(playerScript);
        } catch (parseErr) {
            playerData = eval(`(${playerScript})`);
        }
        
        if (!playerData || !playerData.url) {
            throw new Error('播放数据格式异常: url 缺失');
        }

        let playurl = playerData.url;
        if (/m3u8|mp4/i.test(playurl)) {
            return { parse: 0, url: playurl };
        }

        const configUrl = `${HOST}/static/js/playerconfig.js?t=20251225`;
        const configJs = await requestUtil.request(configUrl);
        if (!configJs) throw new Error('获取 playerconfig.js 失败');

        let MacPlayerConfig = {};
        try {
            const evalCode = `(function(){
                var MacPlayerConfig = {};
                ${configJs.replace(/^var MacPlayerConfig=.*?;/, '')}
                return MacPlayerConfig;
            })()`;
            MacPlayerConfig = eval(evalCode);
        } catch (e) {
            MacPlayerConfig = {
                player_list: {
                    nk1: { parse: 'https://gg.xn--it-if7c19g5s4bps5c.com/nkvod3.php' },
                    nk2: { parse: 'https://gg.xn--it-if7c19g5s4bps5c.com/nkvod3.php' },
                    nk4k: { parse: 'https://gg.xn--it-if7c19g5s4bps5c.com/nkvod3.php' }
                }
            };
        }
        
        const playerList = MacPlayerConfig.player_list || {};
        let parseDomain = playerList[from]?.parse || playerList.nk4k?.parse;

        let jx = '';
        if (parseDomain.includes('?')) {
            jx = `${parseDomain}&url=${encodeURIComponent(playurl)}&next=${encodeURIComponent(playerData.link_next || '')}&title=${encodeURIComponent(playerData.vod_data?.vod_name || '')}`;
        } else {
            jx = `${parseDomain}?url=${encodeURIComponent(playurl)}&next=${encodeURIComponent(playerData.link_next || '')}&title=${encodeURIComponent(playerData.vod_data?.vod_name || '')}`;
        }

        const jxhtml = await requestUtil.request(jx);
        if (!jxhtml) throw new Error('解析接口响应为空');

        let raw_key = [], iv = [], encrypted = '';
        
        const rawKeyMatch = jxhtml.match(/var\s+raw_key\s*=\s*\[([^\]]+)\]/);
        if (rawKeyMatch) {
            raw_key = rawKeyMatch[1].split(',').map(item => parseInt(item.trim())).filter(num => !isNaN(num));
        }
        
        const ivMatch = jxhtml.match(/var\s+iv\s*=\s*\[([^\]]+)\]/);
        if (ivMatch) {
            iv = ivMatch[1].split(',').map(item => parseInt(item.trim())).filter(num => !isNaN(num));
        }
        
        const encryptedMatch = jxhtml.match(/var\s+encrypted\s*=\s*["']([a-fA-F0-9]+)["']/);
        if (encryptedMatch) {
            encrypted = encryptedMatch[1];
        }

        const validKeyLengths = [16, 32];
        const validIVLength = 16;
        if (!encrypted || !validKeyLengths.includes(raw_key.length) || iv.length !== validIVLength) {
            throw new Error(`加密参数提取失败或长度异常 → key:${raw_key.length}, iv:${iv.length}, encrypted:${encrypted.length}`);
        }
        
        const decryptedText = decryptData(encrypted, raw_key, iv);
        
        if (!decryptedText) {
            throw new Error('解密失败');
        }

        let finalPlayUrl = '';
        const randomMatch = decryptedText.match(/getrandom\(['"]([^'"]+)['"]\)/);
        if (randomMatch) {
            finalPlayUrl = getrandom(randomMatch[1]);
        } else {
            const urlPattern = /https?:\/\/[^\s"'<>]+/gi;
            const urlMatches = decryptedText.match(urlPattern);
            if (urlMatches && urlMatches.length > 0) {
                finalPlayUrl = urlMatches[0];
            } else {
                throw new Error('未找到 getrandom 参数或URL');
            }
        }

        return { parse: 0, url: finalPlayUrl };
    } catch (error) {
        return { parse: 1, url: id, error: error.message };
    }
};

// ========== 站点元数据 ==========
const meta = {
    key: "NaiKanYS",
    name: "耐看影视",
    type: 4,
    api: "/video/NaiKanYS"
};

const store = { init: false };
const init = async (server) => {
    if (store.init) return;
    store.log = server.log;
    global.store = store;
    store.init = true;
    
    store.log.info(`耐看影视初始化完成，Node.js版本: ${process.version}`);
};

// ========== 模块导出 ==========
module.exports = async (app, opt) => {
    app.get(meta.api, async (req, reply) => {
        if (!store.init) await init(req.server);
        
        const { extend, filter, t, ac, pg, ext, ids, play, wd, quick } = req.query;

        try {
            if (play) {
                return await _play({ id: play, flags: ext });
            } else if (wd) {
                return await _search({ wd: wd, page: parseInt(pg || "1") });
            } else if (!ac) {
                return await _home({ filter: filter ?? false });
            } else if (ac === "detail") {
                if (t) {
                    const filters = filter ? JSON.parse(filter) : {};
                    return await _category({ id: t, page: parseInt(pg || "1"), filters: filters });
                } else if (ids) {
                    return await _detail({ ids: ids });
                }
            } else if (ac === "homeVod") {
                return await _homeVod({ filter: filter ?? false });
            }
            
            return { code: 404, msg: "未知请求" };
        } catch (e) {
            if (global.store) store.log.error(`请求处理失败: ${e.message}`);
            return { code: 500, msg: "服务器内部错误" };
        }
    });
    
    // 添加清除缓存路由
    app.get(`${meta.api}/clear-cache`, async (req, reply) => {
        cache.clear();
        searchCookie = '';
        if (global.store) store.log.info("缓存和Cookie已清空");
        return { code: 200, msg: "缓存和Cookie已清空" };
    });
    
    opt.sites.push(meta);
};