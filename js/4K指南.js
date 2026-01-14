var rule = {
    title: '4K指南',
    host: 'https://4kzn.com',
    url: '/books/fyclass',
    searchUrl: '/?post_type=book&s=**',
    searchable: 2,
    quickSearch: 0,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    },
    timeout: 10000,
    class_name: '最新电影&最新剧集&系列合集&豆瓣TOP250',
    class_url: 'zuixin&zuixin-juji&xiliehj&top250',
    play_parse: true,
    lazy: $js.toString(() => {
        let url = input.startsWith('push://') ? input : 'push://' + input;
        input = {parse: 0, url: url};
    }),
    
    // 一级：首页列表 - 使用参考文件的选择器优化
    一级: $js.toString(() => {
        try {
            const html = typeof input === 'string' ? input : '';
            if (!html) return [];
            
            // 创建临时DOM解析
            const doc = new DOMParser().parseFromString(html, 'text/html');
            
            // 查找所有电影/剧集项
            const items = [];
            const movieItems = doc.querySelectorAll('.posts-item.book-item');
            
            movieItems.forEach(item => {
                // 提取标题
                const titleEl = item.querySelector('.item-title a');
                const title = titleEl?.textContent?.trim() || titleEl?.title?.trim() || '';
                
                // 提取图片 - 处理懒加载
                const imgEl = item.querySelector('.item-image img');
                let imgSrc = imgEl?.src || imgEl?.getAttribute('data-src') || '';
                
                // 处理相对路径
                if (imgSrc && !imgSrc.startsWith('http')) {
                    if (imgSrc.startsWith('//')) {
                        imgSrc = 'https:' + imgSrc;
                    } else if (imgSrc.startsWith('/')) {
                        imgSrc = 'https://4kzn.com' + imgSrc;
                    }
                }
                
                // 提取描述/质量信息
                const descEl = item.querySelector('.line1.text-muted.text-xs.mt-1');
                const desc = descEl?.textContent?.trim() || '';
                
                // 提取链接
                const linkEl = titleEl || item.querySelector('.item-image a');
                let link = linkEl?.getAttribute('href') || '';
                
                if (link && !link.startsWith('http')) {
                    if (link.startsWith('//')) {
                        link = 'https:' + link;
                    } else if (link.startsWith('/')) {
                        link = 'https://4kzn.com' + link;
                    }
                }
                
                if (title && link) {
                    items.push({
                        title: title,
                        img: imgSrc,
                        desc: desc,
                        url: link
                    });
                }
            });
            
            console.log('提取到项目数量:', items.length);
            return items;
        } catch (e) {
            console.error('解析一级页面出错:', e);
            return [];
        }
    }),
    
    // 二级：详情页
    二级: {
        "title": $js.toString(() => {
            try {
                const html = typeof input === 'string' ? input : '';
                if (!html) return '';
                
                const doc = new DOMParser().parseFromString(html, 'text/html');
                
                // 尝试多种方式获取标题
                const title = 
                    doc.querySelector('.detail-title')?.textContent?.trim() ||
                    doc.querySelector('h1')?.textContent?.trim() ||
                    doc.querySelector('.post-title')?.textContent?.trim() ||
                    '';
                
                console.log('提取的标题:', title);
                return title;
            } catch (e) {
                console.error('提取标题出错:', e);
                return '';
            }
        }),
        
        "img": $js.toString(() => {
            try {
                const html = typeof input === 'string' ? input : '';
                if (!html) return '';
                
                const doc = new DOMParser().parseFromString(html, 'text/html');
                
                // 查找图片
                const imgEl = doc.querySelector('.detail-poster img') || 
                              doc.querySelector('.poster img') || 
                              doc.querySelector('.item-image img');
                
                let imgSrc = imgEl?.src || imgEl?.getAttribute('data-src') || '';
                
                // 处理图片路径
                if (imgSrc && !imgSrc.startsWith('http')) {
                    if (imgSrc.startsWith('//')) {
                        imgSrc = 'https:' + imgSrc;
                    } else if (imgSrc.startsWith('/')) {
                        imgSrc = 'https://4kzn.com' + imgSrc;
                    }
                }
                
                console.log('提取的图片:', imgSrc);
                return imgSrc;
            } catch (e) {
                console.error('提取图片出错:', e);
                return '';
            }
        }),
        
        "desc": $js.toString(() => {
            try {
                const html = typeof input === 'string' ? input : '';
                if (!html) return '';
                
                const doc = new DOMParser().parseFromString(html, 'text/html');
                
                // 提取质量信息
                const quality = doc.querySelector('.quality-tag')?.textContent?.trim() ||
                               doc.querySelector('.resolution')?.textContent?.trim() ||
                               doc.querySelector('.line1.text-muted.text-xs.mt-1')?.textContent?.trim() ||
                               '';
                
                console.log('提取的描述:', quality);
                return quality;
            } catch (e) {
                console.error('提取描述出错:', e);
                return '';
            }
        }),
        
        "content": $js.toString(() => {
            try {
                const html = typeof input === 'string' ? input : '';
                if (!html) return '';
                
                const doc = new DOMParser().parseFromString(html, 'text/html');
                
                // 提取剧情介绍
                const content = doc.querySelector('.plot-description')?.textContent?.trim() ||
                               doc.querySelector('.synopsis')?.textContent?.trim() ||
                               doc.querySelector('.post-content')?.textContent?.trim() ||
                               '';
                
                console.log('提取的内容长度:', content.length);
                return content;
            } catch (e) {
                console.error('提取内容出错:', e);
                return '';
            }
        }),
        
        "tabs": $js.toString(() => {
            // 固定标签为播放地址
            return "['播放地址']";
        }),
        
        "lists": $js.toString(() => {
            try {
                const html = typeof input === 'string' ? input : '';
                if (!html) return [];
                
                const doc = new DOMParser().parseFromString(html, 'text/html');
                
                // 查找播放列表
                const playLists = [];
                
                // 方案1：查找包含"夸克"或"阿里"的链接
                const cloudLinks = doc.querySelectorAll('a');
                const cloudList = [];
                
                cloudLinks.forEach(link => {
                    const text = link.textContent?.trim() || '';
                    const href = link.getAttribute('href') || '';
                    
                    if ((text.includes('夸克') || text.includes('阿里') || text.includes('网盘') || 
                         href.includes('quark') || href.includes('aliyun')) && href) {
                        
                        let displayText = text || '网盘下载';
                        if (!displayText && href.includes('quark')) displayText = '夸克网盘';
                        if (!displayText && href.includes('aliyun')) displayText = '阿里云盘';
                        
                        cloudList.push({
                            text: displayText,
                            url: href.startsWith('http') ? href : 'https://4kzn.com' + (href.startsWith('/') ? '' : '/') + href
                        });
                    }
                });
                
                if (cloudList.length > 0) {
                    playLists.push({
                        title: '网盘下载',
                        episodes: cloudList.map(item => `${item.text}$${item.url}`).join('#')
                    });
                }
                
                // 方案2：查找播放按钮
                const playButtons = doc.querySelectorAll('.play-btn, .play-button, .watch-now');
                const buttonList = [];
                
                playButtons.forEach(button => {
                    const text = button.textContent?.trim() || '播放';
                    const onclick = button.getAttribute('onclick') || '';
                    const href = button.getAttribute('href') || '';
                    
                    if (onclick) {
                        // 尝试从onclick中提取播放地址
                        const match = onclick.match(/window\.open\('([^']+)'\)/) ||
                                     onclick.match(/location\.href='([^']+)'/) ||
                                     onclick.match(/play\('([^']+)'\)/);
                        
                        if (match && match[1]) {
                            buttonList.push({
                                text: text,
                                url: match[1].startsWith('http') ? match[1] : 'https://4kzn.com' + (match[1].startsWith('/') ? '' : '/') + match[1]
                            });
                        }
                    } else if (href) {
                        buttonList.push({
                            text: text,
                            url: href.startsWith('http') ? href : 'https://4kzn.com' + (href.startsWith('/') ? '' : '/') + href
                        });
                    }
                });
                
                if (buttonList.length > 0) {
                    playLists.push({
                        title: '在线播放',
                        episodes: buttonList.map(item => `${item.text}$${item.url}`).join('#')
                    });
                }
                
                console.log('找到播放列表数量:', playLists.length);
                return playLists;
            } catch (e) {
                console.error('提取播放列表出错:', e);
                return [];
            }
        }),
        
        "list_text": "text",
        "list_url": "url"
    },
    
    // 搜索
    搜索: $js.toString(() => {
        try {
            const html = typeof input === 'string' ? input : '';
            if (!html) return [];
            
            const doc = new DOMParser().parseFromString(html, 'text/html');
            
            const items = [];
            // 搜索结果可能使用不同的class
            const searchItems = doc.querySelectorAll('.posts-item.book-item, .search-result-item, .movie-item');
            
            searchItems.forEach(item => {
                // 提取标题
                const titleEl = item.querySelector('h3 a, h4 a, .title a, .item-title a');
                const title = titleEl?.textContent?.trim() || titleEl?.title?.trim() || '';
                
                // 提取图片
                const imgEl = item.querySelector('img');
                let imgSrc = imgEl?.src || imgEl?.getAttribute('data-src') || '';
                
                if (imgSrc && !imgSrc.startsWith('http')) {
                    if (imgSrc.startsWith('//')) {
                        imgSrc = 'https:' + imgSrc;
                    } else if (imgSrc.startsWith('/')) {
                        imgSrc = 'https://4kzn.com' + imgSrc;
                    }
                }
                
                // 提取描述
                const descEl = item.querySelector('.description, .summary, .text-muted');
                const desc = descEl?.textContent?.trim() || '';
                
                // 提取链接
                const linkEl = titleEl || item.querySelector('a');
                let link = linkEl?.getAttribute('href') || '';
                
                if (link && !link.startsWith('http')) {
                    if (link.startsWith('//')) {
                        link = 'https:' + link;
                    } else if (link.startsWith('/')) {
                        link = 'https://4kzn.com' + link;
                    }
                }
                
                if (title && link) {
                    items.push({
                        title: title,
                        img: imgSrc,
                        desc: desc,
                        url: link
                    });
                }
            });
            
            console.log('搜索到项目数量:', items.length);
            return items;
        } catch (e) {
            console.error('解析搜索结果出错:', e);
            return [];
        }
    }),
    
    // 预处理函数
    preRule: $js.toString(() => {
        try {
            const html = typeof input === 'string' ? input : input.html;
            if (html) {
                // 修复懒加载图片
                let fixed = html.replace(/data-src=/g, 'src=');
                
                // 修复相对路径
                fixed = fixed.replace(/src="\/\//g, 'src="https://');
                fixed = fixed.replace(/src="\//g, 'src="https://4kzn.com/');
                
                return { html: fixed };
            }
        } catch(e) {
            console.error('预处理出错:', e);
        }
        return input;
    })
};
