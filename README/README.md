1.本地安装Git，可以去官网下载，也可以去网上搜索，官网下载可能会比较慢。
2.首先在本地创建一个ssh key ，这个的目的就是你现在需要在你电脑上获得一个密匙，获取之后，通过Git bash就可以上位到网上项目中，代码以下：
ssh-keygen -t rsa -C "alanjuntang@163.com"   email@xxx.com是指注册完整邮箱地址

根据默认生成目录找到.ssh中的id_rsa.pub文件，并且用记事本打开。复制其中的值.

打开你浏览器的GitHub设置界面，找到SSH and GPG keys这个选项之后，在网页右上角有一个添加新的SSH keys 点击，标题自己起一个，键就是刚才复制的文件中的值，然后添加。

ssh -T git@github.com  

git config --global user.name "alantang1977"
git config --global user.email "alanchao@163.com"
git clone https://github.com/alantang1977/pg.git


git add .
git commit -m "Enjoy享受"
git push -u origin master  (main或master根据仓库)
