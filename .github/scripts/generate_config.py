name: Generate TV Config

on:
  schedule:
    # 每周五00:00 UTC时间运行（北京时间08:00）
    - cron: '0 0 * * 5'
  workflow_dispatch:  # 允许手动触发
    inputs:
      test_mode:
        description: '运作模式'
        required: false
        default: 'false'
  push:  # 可选：当代码推送到仓库时也运行
    branches: [ main, master ]
    paths:
      - 'py/**'
      - '.github/workflows/generate-config.yml'

jobs:
  generate-config:
    runs-on: ubuntu-latest
    
    permissions:
      contents: write  # 添加写入权限
      pages: write     # 如果使用GitHub Pages
      id-token: write  # 如果使用OIDC
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'
    
    - name: Generate configuration
      run: |
        echo "开始扫描py文件夹..."
        
        # 创建基础JSON结构
        cat > config_base.json << 'EOF'
        {
          "wallpaper": "https://imgs.catvod.com/",
          "logo": "https://cnb.cool/junchao.tang/jtv/-/git/raw/main/Pictures/junmeng.gif",
          "spider": "./jar/custom_spider.jpg",
          "sites": [],
          "headers": [
            {
              "host": "mgtv.ottiptv.cc",
              "header": {
                "User-Agent": "okHttp/Mod-1.4.0.0",
                "Referer": "https://mgtv.ottiptv.cc/"
              }
            }
          ],
          "lives": [
            {
              "name": "冰茶",
              "type": 0,
              "playerType": 2,
              "url": "https://fy.188766.xyz/?ip=&mima=mianfeidehaimaiqian&json=true",
              "ua": "bingcha/1.1(mianfeifenxiang)"
            }
          ],
          "parses": [
            {
              "name": "解析聚合",
              "type": 3,
              "url": "Web"
            },
            {
              "name": "777",
              "type": 0,
              "url": "https://www.huaqi.live/?url="
            },
            {
              "name": "jsonplayer",
              "type": 0,
              "url": "https://jx.jsonplayer.com/player/?url="
            },
            {
              "name": "xmflv",
              "type": 0,
              "url": "https://jx.xmflv.com/?url="
            }
          ],
          "flags": [
            "youku",
            "tudou",
            "qq",
            "qiyi",
            "iqiyi",
            "leshi",
            "letv",
            "sohu",
            "imgo",
            "mgtv",
            "bilibili",
            "pptv",
            "PPTV",
            "migu"
          ],
          "doh": [
            {
              "name": "Google",
              "url": "https://dns.google/dns-query",
              "ips": [
                "8.8.4.4",
                "8.8.8.8"
              ]
            },
            {
              "name": "Cloudflare",
              "url": "https://cloudflare-dns.com/dns-query",
              "ips": [
                "1.1.1.1",
                "1.0.0.1",
                "2606:4700:4700::1111",
                "2606:4700:4700::1001"
              ]
            },
            {
              "name": "AdGuard",
              "url": "https://dns.adguard.com/dns-query",
              "ips": [
                "94.140.14.140",
                "94.140.14.141"
              ]
            },
            {
              "name": "DNSWatch",
              "url": "https://resolver2.dns.watch/dns-query",
              "ips": [
                "84.200.69.80",
                "84.200.70.40"
              ]
            },
            {
              "name": "Quad9",
              "url": "https://dns.quad9.net/dns-query",
              "ips": [
                "9.9.9.9",
                "149.112.112.112"
              ]
            }
          ]
        }
        EOF
        
        # 创建Python脚本来处理配置生成
        cat > generate_config.py << 'EOF'
        import json
        import os
        import re
        from datetime import datetime
        
        def generate_config():
            # 读取基础配置
            with open('config_base.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 扫描py文件夹
            py_dir = './py'
            sites = []
            
            if os.path.exists(py_dir) and os.path.isdir(py_dir):
                print(f"扫描目录: {py_dir}")
                
                # 获取所有.py文件
                py_files = [f for f in os.listdir(py_dir) if f.endswith('.py')]
                print(f"找到 {len(py_files)} 个Python文件")
                
                for py_file in sorted(py_files):
                    file_path = os.path.join(py_dir, py_file)
                    file_name = os.path.splitext(py_file)[0]
                    
                    print(f"处理文件: {py_file}")
                    
                    # 默认配置
                    site_config = {
                        "key": file_name,
                        "name": file_name,
                        "type": 3,
                        "api": f"./py/{py_file}",
                        "searchable": 1,
                        "quickSearch": 0,
                        "filterable": 0,
                        "changeable": 0
                    }
                    
                    # 特殊处理界影视（根据你的需求）
                    if file_name == "界影视":
                        site_config["style"] = {
                            "type": "rect",
                            "ratio": 0.75
                        }
                        site_config["changeable"] = 1
                        # 移除其他不需要的字段
                        site_config.pop("searchable", None)
                        site_config.pop("quickSearch", None)
                        site_config.pop("filterable", None)
                    
                    sites.append(site_config)
            else:
                print(f"警告: 目录 {py_dir} 不存在，使用示例数据")
                # 如果py文件夹不存在，使用示例数据
                sites = [
                    {
                        "key": "飞快TV",
                        "name": "飞快TV",
                        "type": 3,
                        "api": "./py/飞快TV.py",
                        "searchable": 1,
                        "quickSearch": 0,
                        "filterable": 0,
                        "changeable": 0
                    },
                    {
                        "key": "飞快",
                        "name": "飞快",
                        "type": 3,
                        "api": "./py/飞快.py",
                        "searchable": 1,
                        "quickSearch": 0,
                        "filterable": 0,
                        "changeable": 0
                    },
                    {
                        "key": "界影视",
                        "name": "界影视",
                        "type": 3,
                        "api": "./py/界影视.py",
                        "style": {
                            "type": "rect",
                            "ratio": 0.75
                        },
                        "changeable": 1
                    }
                ]
            
            # 更新配置中的sites
            config["sites"] = sites
            
            # 添加生成元数据
            config["_meta"] = {
                "generated_at": datetime.now().isoformat(),
                "generator": "GitHub Action Config Generator",
                "version": "1.0"
            }
            
            # 写入最终配置文件
            output_file = 'tvbox_config.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"配置文件已生成: {output_file}")
            print(f"共添加 {len(sites)} 个站点")
            
            # 也创建一个minified版本
            minified_file = 'tvbox_config.min.json'
            with open(minified_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, separators=(',', ':'))
            
            print(f"压缩版配置文件已生成: {minified_file}")
            
            return output_file, minified_file, len(sites)
        
        if __name__ == "__main__":
            generate_config()
        EOF
        
        # 运行Python脚本
        python generate_config.py
        
        # 显示生成的内容
        echo "=== 生成的配置文件内容 ==="
        cat tvbox_config.json | head -50
        echo ""
        echo "=== 前5个站点 ==="
        cat tvbox_config.json | grep -A 5 '"sites"' | head -20
        
        # 统计信息
        echo "=== 生成统计 ==="
        echo "生成时间: $(date)"
        echo "配置文件大小: $(wc -c < tvbox_config.json) 字节"
        echo "压缩文件大小: $(wc -c < tvbox_config.min.json) 字节"
    
    - name: Create README
      run: |
        echo "创建README文件..."
        
        # 获取站点数量
        SITE_COUNT=$(python -c "
        import json
        with open('tvbox_config.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(len(data['sites']))
        " 2>/dev/null || echo "未知")
        
        cat > README_AUTO_GENERATED.md << 'EOF'
        # 自动生成的TVBox配置
        
        ## 配置文件说明
        
        此配置文件由GitHub Action自动生成，每周五00:00 UTC自动更新。
        
        ### 文件列表
        
        1. **tvbox_config.json** - 完整格式的配置文件
        2. **tvbox_config.min.json** - 压缩格式的配置文件（无空格和换行）
        
        ### 使用方式
        
        将配置文件URL添加到TVBox应用中：
        ```
        https://raw.githubusercontent.com/${{ github.repository }}/refs/heads/main/tvbox_config.json
        ```
        
        或使用压缩版：
        ```
        https://raw.githubusercontent.com/${{ github.repository }}/refs/heads/main/tvbox_config.min.json
        ```
        
        如果启用了GitHub Pages：
        ```
        https://${{ github.repository_owner }}.github.io/$(echo ${{ github.repository }} | cut -d'/' -f2)/tvbox_config.json
        ```
        
        ### 自动扫描
        
        系统会自动扫描 `py/` 文件夹下的所有 `.py` 文件，并为每个文件生成对应的站点配置。
        
        ### 统计信息
        - 站点数量: '$SITE_COUNT'
        - 最后生成时间: $(date)
        - 生成方式: GitHub Action
        
        ### 手动触发
        
        如果需要立即更新配置，可以在仓库的Actions标签页手动运行此工作流。
        
        EOF
        
        echo "README文件创建完成"
    
    - name: Upload artifact
      uses: actions/upload-artifact@v4
      with:
        name: tvbox-config
        path: |
          tvbox_config.json
          tvbox_config.min.json
          README_AUTO_GENERATED.md
        retention-days: 7  # 保留7天
    
    - name: Commit and push generated files
      run: |
        # 配置git
        git config --global user.name "github-actions[bot]"
        git config --global user.email "github-actions[bot]@users.noreply.github.com"
        
        # 添加生成的文件
        git add tvbox_config.json tvbox_config.min.json README_AUTO_GENERATED.md
        
        # 检查是否有变更
        if git diff --staged --quiet; then
          echo "没有文件变更，跳过提交"
        else
          # 提交并推送
          git commit -m "📱 自动更新TVBox配置文件 [skip ci]"
          git push
          echo "文件已提交到仓库"
        fi
    
    - name: Deploy to GitHub Pages (可选)
      if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
      uses: peaceiris/actions-gh-pages@v4
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./
        publish_branch: gh-pages
        keep_files: false
        force_orphan: true
        user_name: 'github-actions[bot]'
        user_email: 'github-actions[bot]@users.noreply.github.com'
